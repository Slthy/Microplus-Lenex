"""
Main application entry point.
Orchestrates the scraping, parsing, and encoding process.
"""
from typing import Optional
from pathlib import Path
import inquirer
from adapters import DataAdapter, MicroplusAdapter
from encoders import Encoder, LenexEncoder
from models import Competition


class CompetitionProcessor:
    """
    Main processor for competition data.
    
    This class orchestrates the entire workflow:
    1. Scrape data from source (if needed)
    2. Parse data into domain models
    3. Encode to target format (LENEX)
    4. Save output
    """
    
    def __init__(
        self,
        adapter: DataAdapter,
        encoder: Encoder,
        data_dir: str = "scraped_data",
        output_dir: str = "processed_data"
    ):
        """
        Initialize processor.
        
        Args:
            adapter: Data adapter for specific timing system
            encoder: Encoder for output format
            data_dir: Directory for scraped data
            output_dir: Directory for encoded output
        """
        self.adapter = adapter
        self.encoder = encoder
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.competition: Optional[Competition] = None
    
    def scrape(self, source: str) -> None:
        """
        Scrape data from source.
        
        Args:
            source: URL or path to data source
        """
        print(f"Scraping data from {source}...")
        self.adapter.scrape_data(source)
        print("Scraping complete!")
    
    def parse(self) -> Competition:
        """
        Parse scraped data into Competition object.
        
        Returns:
            Competition object with all data
        """
        print("Parsing competition data...")
        self.competition = self.adapter.parse_competition()
        print(f"Parsed: {self.competition.name}")
        print(f"  - {len(self.competition.sessions)} sessions")
        print(f"  - {len(self.competition.athletes)} athletes")
        print(f"  - {len(self.competition.clubs)} clubs")
        return self.competition
    
    def encode(self) -> str:
        """
        Encode competition data to target format.
        
        Returns:
            Encoded data string
        """
        if not self.competition:
            raise ValueError("No competition data to encode. Run parse() first.")
        
        print("Encoding to LENEX format...")
        encoded = self.encoder.encode(self.competition)
        print("Encoding complete!")
        return encoded
    
    def save(self, data: str, filename: Optional[str] = None) -> None:
        """
        Save encoded data to file.
        
        Args:
            data: Encoded data string
            filename: Optional custom filename
        """
        if not filename and self.competition:
            filename = self.competition.name.replace(' ', '_')
        elif not filename:
            filename = "competition"
        
        self.encoder.save(data, filename, str(self.output_dir))
    
    def process_full_workflow(self, source: str) -> None:
        """
        Run complete workflow: scrape, parse, encode, save.
        
        Args:
            source: Data source URL or path
        """
        self.scrape(source)
        self.parse()
        encoded = self.encode()
        self.save(encoded)
    
    def process_from_existing(self) -> None:
        """Process data that's already been scraped."""
        self.parse()
        encoded = self.encode()
        self.save(encoded)


class UserInterface:
    """Command-line user interface."""
    
    @staticmethod
    def get_execution_mode() -> str:
        """Get execution mode from user."""
        mode = inquirer.prompt([
            inquirer.List(
                'mode',
                message="Select execution mode",
                choices=[
                    'Scrape and Process',
                    'Process Existing Data',
                    'Scrape Only'
                ]
            )
        ])
        return mode['mode']
    
    @staticmethod
    def get_url() -> str:
        """Get competition URL from user."""
        url = inquirer.prompt([
            inquirer.Text(
                'url',
                message="Enter competition URL",
                validate=lambda _, x: MicroplusAdapter().validate_source(x)
            )
        ])
        return url['url']
    
    @staticmethod
    def get_pool_length() -> str:
        """Get pool length from user."""
        length = inquirer.prompt([
            inquirer.List(
                'length',
                message="Select pool length",
                choices=['LCM (50m)', 'SCM (25m)']
            )
        ])
        return 'LCM' if 'LCM' in length['length'] else 'SCM'
    
    @staticmethod
    def show_success(message: str) -> None:
        """Display success message."""
        print(f"\n✓ {message}\n")
    
    @staticmethod
    def show_error(message: str) -> None:
        """Display error message."""
        print(f"\n✗ Error: {message}\n")


def main():
    """Main application entry point."""
    ui = UserInterface()
    
    print("\n" + "="*50)
    print("Swimming Competition Data Processor")
    print("LENEX 3.0 Encoder for Microplus System")
    print("="*50 + "\n")
    
    try:
        # Get execution mode
        mode = ui.get_execution_mode()
        
        # Initialize processor
        adapter = MicroplusAdapter()
        encoder = LenexEncoder()
        processor = CompetitionProcessor(adapter, encoder)
        
        if mode == 'Scrape and Process':
            url = ui.get_url()
            processor.process_full_workflow(url)
            ui.show_success("Complete workflow finished successfully!")
        
        elif mode == 'Process Existing Data':
            processor.process_from_existing()
            ui.show_success("Processing complete!")
        
        elif mode == 'Scrape Only':
            url = ui.get_url()
            processor.scrape(url)
            ui.show_success("Scraping complete! Data saved to scraped_data/")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    
    except Exception as e:
        ui.show_error(str(e))
        raise


if __name__ == "__main__":
    main()