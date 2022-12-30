from functions import scrape_data, build_lenex

def main():
    config = {
        'url': 'https://fin2022.microplustiming.com/NU_2022_07_28-08_04_Roma_web.php'
    }
    #scrape_data(config['url'])
    build_lenex()
    
if __name__ == "__main__":
    main()
