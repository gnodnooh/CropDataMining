import os
import urllib.request
from bs4 import BeautifulSoup
import numpy as np


def LinkFromURL(url):
    '''
    Returns all hyperlinks in the URL.
    '''
    # Retreive links in the URL path
    urlpath = urllib.request.urlopen(url)
    html_doc = urlpath.read().decode('utf-8')
    # BeautifulSoup object
    soup = BeautifulSoup(html_doc, 'html.parser')
    # Make a list of hyerlinks
    links = []
    for link in soup.find_all('a'):
        links.append(link.get('href'))
    links.pop(0)     # Remove the parent link        
    return links


def DownloadFromURL(fullURL, fullDIR, showLog = False):
    '''
    Downloads the inserted hyperlinks (URLs) to the inserted files n the disk
    '''
    # Make parent directories if they do not exist
    if type(fullDIR) == list:
        parentDIRS = list(np.unique([os.path.dirname(DIR) for DIR in fullDIR]))
        for parentDIR in parentDIRS:
            os.makedirs(parentDIR, exist_ok=True)
        # Download all files
        nError = 0
        nExist = 0
        nDown = 0
        for file_url, file_dir in zip(fullURL, fullDIR):
            if not os.path.exists(file_dir):
                try:
                    urllib.request.urlretrieve(file_url, file_dir)
                    nDown += 1
                    print(file_dir, 'is saved.')
                except:
                    nError += 1
                    pass
            else:
                nExist += 1
        if showLog:
            print('%d files are tried: %d exist, %d downloads, %d errors' % (len(fullURL),nExist,nDown,nError))
            
    elif type(fullDIR) == str:
        parentDIRS = os.path.dirname(fullDIR)
        # Download all files
        nError = 0
        nExist = 0
        nDown = 0
        if not os.path.exists(fullDIR):
                try:
                    urllib.request.urlretrieve(fullURL, fullDIR)
                    nDown += 1
                    print(fullDIR, 'is saved.')
                except:
                    nError += 1
                    pass
                else:
                    nExist += 1
        if showLog:
            print('%d files are tried: %d exist, %d downloads, %d errors' % (len(fullURL),nExist,nDown,nError))
    return


def main():
    url = 'https://www.ncei.noaa.gov/data/avhrr-land-normalized-difference-vegetation-index/access/'
    path = '/Users/dlee/data/repo/CropYieldForecast/ndvi/'
    year = 1981
    links = LinkFromURL(url+str(year))
    links = [link for link in links if link.startswith('AVHRR')]
    fullDIR = [os.path.join(path, link) for link in links]
    fullURL = [os.path.join(url, str(year), link) for link in links]
    DownloadFromURL(fullURL, fullDIR, True)
    
    
if __name__ == "__main__":
    main()