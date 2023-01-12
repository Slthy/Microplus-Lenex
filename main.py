import inquirer
import re
from functions import scrape_data, build_lenex, write_file, debug


def main():
    mode = inquirer.prompt([inquirer.List('mode', message="Execution mode", choices=[
                            'Scrape and Compile', 'Compile only', 'Debug'])])['mode']
    if mode == 'Scrape and Compile':
        scrape_data(inquirer.prompt([inquirer.Text('url', message="Insert competition's url",
                    validate=lambda _, x: re.match(
                        'https://fin\d\d\d\d\.microplustiming\.com/NU_.*web\.php', x),
        )])['url'])
    elif mode == 'Debug':
        debug(build_lenex())
        exit()
        
    
    write_file(build_lenex())



if __name__ == "__main__":
    main()
