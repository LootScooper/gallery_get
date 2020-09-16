import time
import threading
from queue import Queue
import re
from bs4 import BeautifulSoup
from urllib.request import urlopen
# from sys import argv

import pyperclip
import gallery_get


def is_imagefap(url):
    if url.startswith("https://www.imagefap.com"):
        print("Found url: %s" % str(url))
        return True
    return False


DOWNLOAD_QUEUE = Queue()
EXTRACTION_QUEUE = Queue()


def sort_url(url):
    if bool(re.match("(?s)^https://www.imagefap.com/pictures/[0-9]+/.*", url)):
        DOWNLOAD_QUEUE.put(url)
    if bool(re.match("(?s)^https://www.imagefap.com/(?:profile|organizer)/[0-9]+/.*", url)):
        EXTRACTION_QUEUE.put(url)


class ClipboardWatcher(threading.Thread):
    def __init__(self, predicate, callback, pause=5.):
        super(ClipboardWatcher, self).__init__()
        self._predicate = predicate
        self._callback = callback
        self._pause = pause
        self._stopping = False

    def run(self):
        recent_value = ""

        while not self._stopping:
            tmp_value = pyperclip.paste()
            if tmp_value != recent_value:
                recent_value = tmp_value

                for url in recent_value.splitlines():
                    if self._predicate(url):
                        self._callback(url)
            time.sleep(self._pause)

    def stop(self):
        self._stopping = True


class LinkExtractor(threading.Thread):
    def __init__(self, pause=5.):
        super().__init__()
        self._stopping = False
        self._pause = pause

    @staticmethod
    def get_links(url):
        html_page = urlopen(url)
        soup = BeautifulSoup(html_page, features="lxml")
        links = []

        for link in soup.findAll('a', attrs={'href': re.compile("^/gallery")}):
            links.append("https://www.imagefap.com" + link.get('href'))

        return links

    def run(self):
        while not self._stopping:
            for gallery_url in self.get_links(EXTRACTION_QUEUE.get()):
                DOWNLOAD_QUEUE.put(gallery_url)
            time.sleep(self._pause)

    def stop(self):
        self._stopping = True


class Downloader(threading.Thread):
    def __init__(self, location, pause=5.):
        super().__init__()
        self._stopping = False
        self._pause = pause
        self._location = location

    def run(self):
        while not self._stopping:
            try:
                gallery_url = DOWNLOAD_QUEUE.get()
                print("Downloading " + gallery_url)
                gallery_get.run(gallery_url, self._location)
            except Exception as e:
                print(e)
            time.sleep(self._pause)

    def stop(self):
        self._stopping = True


def main():
    # download_location = argv[1]
    download_location = "V:\\imagefap\\test"

    downloader = Downloader(download_location, 5)
    extractor = LinkExtractor(5)
    watcher = ClipboardWatcher(
        is_imagefap,
        sort_url,
        3.
    )

    downloader.start()
    extractor.start()
    watcher.start()

    while True:
        try:
            # print("Waiting for changed clipboard...")
            time.sleep(3)
        except KeyboardInterrupt:
            watcher.stop()
            extractor.stop()
            downloader.stop()
            break


if __name__ == "__main__":
    main()
