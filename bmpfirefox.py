from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
import time
import argparse
import os

import har_rip

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
#logger = logging.getLogger(__name__)

def log(message, logger=None):
    if logger is not None:
        logger.warning(message)
    else:
        print(message)

class ProxyManager:
    __BMP = "/home/my_user/my_folder/bmp_bin/browsermob-proxy-2.1.4/bin/browsermob-proxy"

    def __init__(self):
        self.__server = Server(ProxyManager.__BMP)
        self.__client = None
    
    def start_server(self):
        self.__server.start(options={'log_path':'/var/log/my_folder/', 'log_file':'abmplogfile'})
        #self.__server.start()
        return self.__server

    def start_client(self):
        self.__client = self.__server.create_proxy()
        return self.__client

    @property
    def client(self):
        return self.__client    
    
    @property
    def server(self):
        return self.__server

def set_browser_options(opts):
    
    # --------------- w3c/user agent supposed to help with the issues
    #opts.w3c = True
    opts.add_argument("--user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'")
    #from fake_useragent import UserAgent
    #ua = UserAgent()
    #userAgent = ua.random
    #print(userAgent)
    #opts.add_argument(f'user-agent={userAgent}')

    # ------------- Set window size
    opts.add_argument("--window-size=2048,2048")

    # ------------ Headless, disable GPU
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu') # NOT APPLICABLE TO FIREFOX ?

if __name__ == "__main__":
    # Args
    parser = argparse.ArgumentParser(description='Rip chapters from source.')
    parser.add_argument('url', type=str, help='URL to rip (e.g. https://....')
    parser.add_argument('-k', '--key', type=str, help='Account sessionid for chapters to unlock')
    args = parser.parse_args()
    target = args.url
    debug = False

    # Validate url
    my_urls = ("firsturl", "secondurl")
    if not target.lower().startswith(my_urls):
        exit(-1)
    # Check if chapter doesn't already exist, get chap_title
    chap_title = har_rip.chap_exists(target)

    # Check crude semaphore system
    while(os.path.isfile("/home/my_user/my_folder/files/hellobmp")):
        time.sleep(3)
    os.system("touch /home/my_user/my_folder/files/hellobmp") # get our seat

    # Recheck just in case previous requests didn't download said chapter
    directory = f"/home/my_user/my_folder/files/{chap_title}"
    if os.path.exists(directory) and os.path.isfile(f"{directory}.zip"):
        os.system("rm /home/my_user/my_folder/files/hellobmp") # we're leaving instantly
        print(f"{directory}.zip")
        exit(0)

    try:
        # Set BMP proxy
        proxy = ProxyManager()
        server = proxy.start_server()
        client = proxy.start_client()
        client.new_har(target)

        if debug:
            myProx = client.proxy
            myPort = int(myProx.split(":")[1])
            myProxy = f"127.0.0.1:{myPort}"

            log(f"Server : {server}")
            log(f"Proxy : {client.proxy}")
            log(f"My Proxy : {myProxy}")
            log("-----------------------------------\n\n")

        # Set options
        opts = webdriver.FirefoxOptions()
        set_browser_options(opts)

        # Set profile?
        profile = webdriver.FirefoxProfile()
        profile.set_proxy(client.selenium_proxy())

        har_content = None
    
    except Exception as e:
        log("BMP failed.")
        log(repr(e))
        server.stop()
        os.system("rm /home/my_user/my_folder/files/hellobmp")
        os.system("/bin/bash /home/my_user/my_folder/clean.sh")
        log("Finished cleanup")
        exit(-1)

    # Launch browser
    try:
        log("Initialize driver")
        driver = webdriver.Firefox(service_log_path=None, executable_path="/home/my_user/my_folder/geckodriver", options=opts, firefox_profile=profile)

        driver.set_window_size(2048, 2048)
        log(driver.get_window_size())
        log("\n----------------")

        log("Load page ...")
        driver.get(target)
        # Set cookies
        if args.key is not None:
            driver.add_cookie({"name":"sessionid", "value":args.key, "domain": "my_website.com"})
        log("Reload page ...")
        driver.get(target)
        log("Sleeping ...")
        time.sleep(6)
        log("Finished sleeping")

        # Get pages number
        elem = driver.find_element(By.CLASS_NAME, "br-slider__pagenum-last")
        nb_pages = int(elem.get_attribute('innerHTML'))
        log(f"Number of pages : {nb_pages}")

        # Send left keys for half the amount of pages
        body = driver.find_element(By.XPATH, "//body")
        for i in range(min(int(nb_pages/2), 40)):
            body.send_keys(Keys.LEFT)
            time.sleep(2)

        thehar = str(client.har)
        print("Finished running through pages")
        server.stop()
        print("Stopped server")
        driver.quit()
        print("Driver stopped")
        os.system("/bin/bash /home/my_user/my_folder/clean.sh")
        print("Cleaned")

        print("done")
        har_content = thehar



    except Exception as e:
        log("Selenium failed.")
        log(repr(e))
        log("Starting cleanup")
        server.stop()
        os.system("/bin/bash /home/my_user/my_folder/clean.sh")
        driver.quit()
        os.system("rm /home/my_user/my_folder/files/hellobmp")
        log("Finished cleanup")
        exit(-1)

    if har_content is None:
        os.system("rm /home/my_user/my_folder/files/hellobmp")
        exit(-1)
    else:
        har_rip.rip_har(har_content, chap_title)