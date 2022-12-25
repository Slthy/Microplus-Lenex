from functions import scrape_data, get_sessions

def main():
    config = {
        'url': 'https://fin2022.microplustiming.com/NU_2022_07_28-08_04_Roma_web.php'
    }
    scrape_data(config['url'])
    competition = get_sessions()
    
if __name__ == "__main__":
    main()
