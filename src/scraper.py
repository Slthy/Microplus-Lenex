import requests
import pathlib
import json
import utils  # Make sure 'utils.py' with FILE_TYPES is in your 'src' folder

class MeetScraper:
    """Handles downloading all meet data from the source."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.replace('/NU', '/export/NU').replace('_web.php', '')
        self.scraped_data_dir = "scraped_data"
        print(f"Scraper initialized for base URL: {self.base_url}")

    def scrape_all_data(self):
        """
        Main scraping function.
        Downloads all JSON files and stores them in 'scraped_data'.
        """
        print("Starting scrape...")
        try:
            counter_url = f'{self.base_url}/NU/CounterGenerale.json?'
            counter_generale = requests.get(counter_url).text[:-2]
            
            contatori_url = f'{self.base_url}/NU/Contatori.json?x={counter_generale}'
            contatori = requests.get(contatori_url).json()['contatori']
        except requests.RequestException as e:
            print(f"Error fetching counter files: {e}")
            return
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from counters: {e}")
            return

        for obj in contatori:
            try:
                file_url = f'{self.base_url}/NU/{obj["nomefile"]}?x={obj["counter"]}'
                scraped_data = requests.get(file_url).json()

                file_type = utils.FILE_TYPES.get(obj['cod'], "other")
                target_dir = pathlib.Path(f'{self.scraped_data_dir}/{file_type}')
                target_dir.mkdir(parents=True, exist_ok=True)

                # Use 'jsonfilename' from the downloaded data for the file name
                file_name = scraped_data["jsonfilename"]
                target_path = target_dir / file_name
                
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(scraped_data, f, indent=2) # Save formatted JSON
                
                print(f"Saved: {target_path}")

            except requests.RequestException as e:
                print(f"Error downloading {self.base_url}: {e}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.base_url}")
            except KeyError:
                print(f"Error: 'jsonfilename' not found in {self.base_url}")
            except Exception as e:
                print(f"An unexpected error occurred for {obj['nomefile']}: {e}")