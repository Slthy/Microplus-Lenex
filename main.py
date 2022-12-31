import inquirer
import re
from functions import scrape_data, build_lenex


def main():
    '''
    mode = inquirer.prompt([inquirer.List('mode', message="Execution mode", choices=[
                            'Scrape and Compile', 'Compile only'])])['mode']
    if mode == 'Scrape and Compile':
        scrape_data(inquirer.prompt([inquirer.Text('url', message="Insert competition's url",
                    validate=lambda _, x: re.match(
                        'https://.*[0-9]+\.microplustiming\.com/NU_([0-9]+(_[0-9]+)+)-([0-9]+(_[0-9]+)+)_[a-zA-Z]+_web\.php', x),
        )])['url'])
    '''
    build_lenex()



if __name__ == "__main__":
    main()
