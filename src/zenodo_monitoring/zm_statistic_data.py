import pandas as pd
import plotly.express as px

from src.models.deposit_model import DepositDAO
from src.models.frame_model import FrameDAO

class StatisticData:
    def __init__(self) -> None:
        
        self.deposit_manager = DepositDAO()
        self.frame_manager = FrameDAO()


    def get_platform_by_session_chart(self):
        """ Extract platform by session name  pie chart. """
        # Extract platform value.
        deposits = self.deposit_manager.deposits
        platforms = [] if len(deposits) == 0 else [deposit.platform for deposit in deposits]
        self.platform_type = list(set(platforms))
        platform_counts = {b: platforms.count(b) for b in set(platforms)}
        
        df = pd.DataFrame(list(platform_counts.items()), columns=['Plaftorm', 'Count'])
        
        # Create the pie chart
        fig = px.pie(df, names='Plaftorm', values='Count', title='Plaftorm Distribution')

        return fig
    
    def get_platform_by_frames_chart(self):
        """ Extract platform by frame count. """        
        platform_by_frame_count = self.frame_manager.get_number_images_by_platform()
        df = pd.DataFrame(list(platform_by_frame_count.items()), columns=['Plaftorm', 'Count'])
        
        # Create the pie chart
        fig = px.pie(df, names='Plaftorm', values='Count', title='Frame count by platform type')

        return fig