from ..adapters.data_source import IMeetDataSource
from ..core.serializer import LenexSerializer
from ..model.meet import Meet


class LenexEncoder:
    """
    Orchestrates the entire conversion process.

    This class coordinates the adapter (which fetches and transforms
    data) and the serializer (which writes the final XML).
    It contains no complex business logic itself, making it
    clean and easy to maintain.
    """

    def __init__(self, data_source: IMeetDataSource):
        """
        Initializes the encoder with a specific data source adapter.

        This uses "Dependency Injection," allowing the encoder
        to work with any adapter (e.g., ScrapedDataAdapter, ApiAAdapter)
        as long as it follows the IMeetDataSource interface.

        Args:
            data_source (IMeetDataSource): An instance of a class
                that implements the IMeetDataSource interface.
        """
        if not hasattr(data_source, 'get_meet_object'):
            raise TypeError("data_source must be an adapter that "
                            "implements the IMeetDataSource interface")
        self.data_source = data_source
        print("Encoder: Initialized with adapter.")

    def build_meet(self) -> Meet:
        """
        Builds the full Meet object graph from the data source.

        This method runs the adapter's main logic to load, parse,
        and transform all the raw data into the clean,
        OOP data class model.
        """
        print("Encoder: Asking data source to build meet object...")
        meet_object = self.data_source.get_meet_object()
        print("Encoder: Received populated meet object from adapter.")
        return meet_object

    def generate_xml(self) -> str:
        """
        Generates the final, formatted Lenex XML string.

        This is the main method to get the final output. It
        orchestrates the full process:
        1. Gets the Meet object from the adapter.
        2. Passes the Meet object to the serializer.
        3. Returns the resulting XML string.
        """
        # Get the populated data model
        meet = self.build_meet()

        # Pass the complete model to the serializer
        print("Encoder: Passing meet object to serializer...")
        serializer = LenexSerializer(meet=meet)
        
        # Get the final XML string from the serializer
        xml_output = serializer.to_xml_string()
        print("Encoder: Received final XML string from serializer.")

        return xml_output