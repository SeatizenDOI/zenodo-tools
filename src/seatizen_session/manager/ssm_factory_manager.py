from pathlib import Path

from .ssm_uav_session import UAVSession
from .ssm_default_session import DefaultSession
from .ssm_base_manager import BaseSessionManager

class FactorySessionManager:

    @staticmethod
    def get_session_manager(session_path: str, temp_folder: str) -> BaseSessionManager:
        
        # Extract platform in session name.
        session_platform = Path(session_path).name.split("_")[2].split("-")[0].upper()

        if session_platform == "UAV":
            return UAVSession(session_path, temp_folder)

        return DefaultSession(session_path, temp_folder)


