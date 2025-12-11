from abc import ABC, abstractmethod
from typing import List
from ..model.meet import Meet # Assuming you have a Meet model
from ..model.event import Event


class IMeetDataSource(ABC):
    """
    Interface for a data source. All adapters must implement these methods.
    """
    @abstractmethod
    def get_meet_details(self) -> Meet:
        """Fetch the top-level meet information."""
        pass

    @abstractmethod
    def get_all_events(self) -> List[Event]:
        """Fetch all events for the meet."""
        pass

    @abstractmethod
    def get_processed_results(self, event_id: str) -> List[ProcessedResult]:
        """
        Fetch and transform results for a specific event.
        # TODO: ProcessedResult class
        """
        pass