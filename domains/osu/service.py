import logging

from core.llm.pool import llm_pool
from core.llm.prompts import HELITH_PERSONALITY
from domains.osu.client import osu_api_client
from domains.osu.ml_model import (
    calculate_improvement_indicator,
    predict_days_to_rank,
)
from domains.osu.models import OsuSnapshot
from domains.osu.repository import osu_repo

logger = logging.getLogger("helith.osu.service")


class OsuService:
    """Core coordination service for osu! rank prediction."""

    async def process_slash_predict(
        self, username: str, target_rank: int, server_id: str, user_id: str
    ) -> str:
        """Processes the structural prediction from a Slash Command.

        1. Queries current and historical data from the osu! API.
        2. Registers the progress snapshot in the DB.
        3. Calculates the Improvement Indicator and runs the log-linear regression.
        4. Generates the final response using Helith's personality.
        """
        logger.info(
            f"Processing osu! prediction for: '{username}' to rank '{target_rank}'"
        )

        if target_rank <= 0:
            target_rank = 5000

        # 1. Query data from the osu! API (or mock)
        user_data = await osu_api_client.get_user_data(username)
        if not user_data:
            return (
                f"I could not find user '{username}' on osu!. "
                "Please verify that the username is valid."
            )

        osu_id = user_data["osu_id"]
        actual_username = user_data["username"]
        current_rank = user_data["global_rank"]
        pp = user_data["pp"]
        play_time = user_data["play_time"]
        rank_history = user_data["rank_history"]

        # 2. Calculate the Improvement Indicator (ii)
        ii = calculate_improvement_indicator(pp, play_time)

        # 3. Register daily progress snapshot in the database
        snapshot = OsuSnapshot(
            osu_id=osu_id,
            username=actual_username,
            global_rank=current_rank,
            pp=pp,
            play_time=play_time,
            improvement_indicator=ii,
        )
        osu_repo.save_snapshot(snapshot)

        # 4. Generate the time series for the regression
        if not rank_history or len(rank_history) < 2:
            history_series = [(0, current_rank), (1, current_rank)]
        else:
            history_series = [(i, rank) for i, rank in enumerate(rank_history)]

        # 5. Train and predict
        prediction = predict_days_to_rank(history_series, target_rank, ii)

        # 6. Draft final response with LLM pool maintaining identity
        response = await self._generate_conversational_response(
            actual_username=actual_username,
            current_rank=current_rank,
            pp=pp,
            target_rank=target_rank,
            ii=ii,
            model_message=prediction["message"],
            user_id=user_id,
            server_id=server_id,
        )

        return response

    async def _generate_conversational_response(
        self,
        actual_username: str,
        current_rank: int,
        pp: float,
        target_rank: int,
        ii: float,
        model_message: str,
        user_id: str,
        server_id: str,
    ) -> str:
        """Asks the LLM to write the mathematical prediction using Helith's
        exact personality.
        """
        prompt = (
            "Present the results of the osu! rank predictive analysis "
            "in a serious, direct, and analytical manner.\n"
            f"Player: {actual_username}\n"
            f"Current rank: #{current_rank:,} (PP: {pp:.2f})\n"
            f"Target rank: #{target_rank:,}\n"
            f"Improvement Index (ii): {ii:.2f}\n"
            f"Mathematical result of the model: {model_message}\n\n"
            "Writing instructions:\n"
            "- Speak in the first person, maintaining Helith's identity "
            "(reserved, sober, straightforward).\n"
            "- Emphasize logical analysis and interpret the numbers.\n"
            "- Keep the response concise (maximum 3-4 lines).\n"
            "- Avoid informal greetings, childish emojis, or customer "
            "service pleasantries."
        )

        try:
            return await llm_pool.generate_response(
                prompt=prompt,
                system_prompt=HELITH_PERSONALITY,
                server_id=server_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Error generating conversational response with the LLM: {e}")
            # Direct fallback return if LLM fails
            return (
                f"Analysis for {actual_username}: Current rank #{current_rank:,} "
                f"({pp:.2f} PP). Target rank #{target_rank:,}. {model_message}"
            )


osu_service = OsuService()
