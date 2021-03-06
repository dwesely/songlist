# -*- coding: utf-8 -*-
"""
Created on Fri May 20 22:03:45 2016

songlist.py

Purpose: Parse a folder full of tab-separated files containing historical information
on the use of hymns, to be used as a planning tool to reduce back-to-back usage of
hymns, but also provide a list of hymns with familiarity to be used as a baseline
repertoire.

Script downloads latest sheet using details in account.txt, then uploads the results

@author: Wesely
"""

from __future__ import print_function
import httplib2

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import re
from datetime import date,datetime
from datetime import timedelta
import os

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

DOWNLOAD_AND_UPDATE = True 
# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-mysongbot.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = ''
APPLICATION_NAME = 'MySongBot'

#File management
OUTPUT_FILENAME  = 'songlistReport.txt'
LOG_FILENAME     = 'log.txt'
ACCOUNT_FILENAME = 'account.txt'

#Header on the date column is inconsistent, but it is consistently in the first column
DATECOLUMN = 0

VERBOSE = True

#http://stackoverflow.com/questions/16139306/determine-season-given-timestamp-in-python-using-datetime
Y = 2000 # dummy leap year to allow input X-02-29 (leap day)
seasons = [(0, (date(Y,  1,  1),  date(Y,  3, 20))),
           (1, (date(Y,  3, 21),  date(Y,  6, 20))),
           (2, (date(Y,  6, 21),  date(Y,  9, 22))),
           (3, (date(Y,  9, 23),  date(Y, 12, 20))),
           (0, (date(Y, 12, 21),  date(Y, 12, 31)))]
seasonList = ['winter','spring','summer','fall']
def get_season(now):
    if isinstance(now, datetime):
        now = now.date()
    now = now.replace(year=Y)
    return next(season for season, (start, end) in seasons
                if start <= now <= end)

class Song:

    songs_dict = {}

    def __init__(self, number, title):
        self.title         = title.strip('\n\t\r ')
        self.number        = number
        self.dates         = set([]) #set of all dates used
        self.firstCount    = 0
        self.middleCount   = 0
        self.lastCount     = 0
        
        Song.songs_dict[number] = self
        
        if title not in SongTitle.songTitles_dict:
            SongTitle(number,title)
    def add_date(self, date):
        self.dates.add(date) #should be datetime objects
    def increment_firstCount(self):
        self.firstCount = self.firstCount + 1
    def increment_middleCount(self):
        self.middleCount = self.middleCount + 1
    def increment_lastCount(self):
        self.lastCount = self.lastCount + 1
def getSong(number, title):
    if VERBOSE:
        print('Getting song # {}, called {}'.format(number,title))
    if number not in Song.songs_dict:
        songObj = Song(number, title)
        if VERBOSE:
            print('Saved #{}: {}'.format(number,title))
    else:
        songObj = Song.songs_dict.get(number)
    return songObj

class SongTitle:
    #Keep list of unique titles to identify missing song numbers
    songTitles_dict = {}

    def __init__(self, number, title):
        self.title         = title.strip('\n\t\r ')
        self.number        = number
        self.useCount      = 1
        self.matchCount    = 0
        
        SongTitle.songTitles_dict[title] = self
def getSongTitle(number, title):
    if VERBOSE:
        print('Getting song # {}, called {}'.format(number,title))
    if title not in SongTitle.songTitles_dict:
        songTitleObj = SongTitle(number, title)
        if VERBOSE:
            print('Saved #{}: {}'.format(number,title))
    else:
        songTitleObj = SongTitle.songTitles_dict.get(title)
    return songTitleObj
def getSongNumber(title):
    songTitleObj = []
    title = title.strip('\n\t\r "')
    if VERBOSE:
        print('Getting song titled {}'.format(title))
    #TODO: save unmatched song titles to separate set and count those as well
    if title:
        if isinstance(title, basestring):
            for songTitle in SongTitle.songTitles_dict.values():
                if title.upper() in songTitle.title.upper():
                    songTitleObj = songTitle
                    songTitleObj.matchCount = songTitleObj.matchCount + 1
                    return songTitleObj
    else:
        if VERBOSE:
            print('Title is empty string.')
    return songTitleObj

class ServiceDate:
    #Keep list of unique titles to identify missing song numbers
    serviceDate_dict = {}

    def __init__(self, date, poc, rawSongString):
        self.date          = date #should be datetime object
        #https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
        self.poc           = poc
        self.rawSongString = rawSongString
        self.dates         = set([]) #set of all songs referenced
        self.parsed        = False
        
        ServiceDate.serviceDate_dict[date] = self
        self.parseRawSongString()
    def parseRawSongString(self):
        if VERBOSE:
            print('\nProcessing raw string for date {}'.format(self.date.isoformat()))
            print('Raw string: {}'.format(self.rawSongString))
        if not self.rawSongString:
            if VERBOSE:
                print('No raw song string for date {}'.format(self.date.isoformat()))
        else:
            
            #Cleaning
            cleanedSongString = self.rawSongString.replace('TENTATIVE: ','')
            cleanedSongString = re.sub(r'\d+:\d+',' ',cleanedSongString) #remove service times
            cleanedSongString = cleanedSongString.replace('_x000a',' ')
            cleanedSongString = cleanedSongString.replace('\d+:\d+',' ')
            if ':' in cleanedSongString:
                print('Found colon in cleaned string:\n\t{}'.format(cleanedSongString))
                ##TODO: remove all preambles (e.g. "Tentative:"), split on colon to handle multiple services
            
            numbersFound = re.findall(r'\d+',cleanedSongString)
            lettersFound = re.findall(r'[a-zA-Z]',cleanedSongString)
            semicolonFound = ';' in cleanedSongString
            
            #if no semicolon:
            if (len(lettersFound) < 1 or len(numbersFound) > 1) and not semicolonFound:
                #could just be a single song
                cleanedSongString = re.sub(r'[#_, ]+(\d+)',r';\1',cleanedSongString)
                cleanedSongString = re.sub(r'^;','',cleanedSongString)
                if VERBOSE:
                    print(cleanedSongString)
                #TODO: identify if digits are in front or in back of the titles (find first digit, count index, if <5, digits are in front)
                #replace non-word characters in front/behind the digits with semicolons
                #r('(\W+\d+)')
            
            #split recorded songs (typically semicolon or comma separating multiple entries)
            individualSongs = cleanedSongString.split(';')
            if VERBOSE:
                print(individualSongs)
            
            for songidx,songStr in enumerate(individualSongs):
                #parse song title and number
                #song number first:
                #TODO: This logic is weird, need to clean this up
                numberOnly  = re.search(r'\D*(\d+)\D*',songStr)
                numberTitle = re.search(r'\D*(\d+)\W*(\D+[^;]+)',songStr)
                if not numberTitle:
                    if numberOnly:
                        if VERBOSE:
                            print('Number only: {}'.format(numberOnly.group(0)))
                        songNumber = numberOnly.group(0)
                        songTitle  = ''
                    else:
                        titleObj = getSongNumber(songStr)
                        if titleObj:
                            songNumber = titleObj.number
                            if VERBOSE:
                                print('No number identified for song: {}, using {}'.format(songStr,songNumber))
                        else:
                            if VERBOSE:
                                print('No number identified for song: {}'.format(songStr))                            
                            return
                    if VERBOSE:
                        print('Song {} not parsed.'.format(songStr))

                elif not numberTitle.group(2).strip(' \t\n\r'):
                    if VERBOSE:
                        print('No title for song {}'.format(numberTitle.group(1)))
                    if numberOnly:
                        if VERBOSE:
                            print('Number only: {}'.format(numberOnly.group(0)))
                        songNumber = numberOnly.group(0)
                        songTitle  = ''
                    else:
                        titleObj = getSongNumber(songStr)
                        if titleObj:
                            songNumber = titleObj.number
                            if VERBOSE:
                                print('No number identified for song: {}, using {}'.format(songStr,songNumber))
                        else:
                            if VERBOSE:
                                print('No number identified for song: {}'.format(songStr))                            
                            return
                else:
                    songNumber = numberTitle.group(1).strip(' \t\n\r')
                    songTitle  = numberTitle.group(2).strip(' \t\n\r')
                    self.parsed = True                    
                    #save song
                songObj = getSong(songNumber, songTitle)
                #TODO: Check if the song is already saved in this date - don't want to double count songs
                if songObj:
                    songObj.add_date(self.date)
                    if songidx == 0:
                        songObj.firstCount = songObj.firstCount + 1
                    elif songidx == len(individualSongs)-1:
                        songObj.lastCount = songObj.lastCount + 1
                    else:
                        songObj.middleCount = songObj.middleCount + 1
                        
                titleObj = getSongTitle(songNumber,songTitle)
                if titleObj:
                    titleObj.useCount = titleObj.useCount + 1

                #record placement (first/middle/last)
            
            if VERBOSE:
                print('Successfully parsed {}'.format(cleanedSongString))
        
def getServiceDate(date):
    if date not in ServiceDate.serviceDate_dict:
        if VERBOSE:
            print('Service Date "{}" not found in list.'.format(date))
        serviceDateObj = []
    else:
        serviceDateObj = ServiceDate.serviceDate_dict.get(date)
    return serviceDateObj
    
def getDatedSheet():
    #get current sheet name
    if int(date.today().strftime('%m')) > 8:
        currentSheetName = 'Sept {} - Aug {}'.format(date.today().strftime('%Y'),int(date.today().strftime('%Y'))+1)
    else:
        currentSheetName = 'Sept {} - Aug {}'.format(int(date.today().strftime('%Y'))-1,date.today().strftime('%Y'))
    return currentSheetName

def getAccountDetails():
    #Read document and client file details
    accountFilename  = ACCOUNT_FILENAME
    docid            = None
    clientSecretFile = None
    
    with open(accountFilename, 'r') as accountDetails:
        allLines = re.split(r'\n',accountDetails.read())
        for line in allLines:
            if 'docid:' in line:
                docid      = re.sub(r'docid:\s*'     ,'',line)
            elif 'clientSecretFile: ' in line:
                clientSecretFile = re.sub(r'clientSecretFile:\s*','',line)
    return (docid,clientSecretFile)



def get_credentials(clientSecretFile):
    #From google api quick start - need credentials before downloading/uploading
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-mysongbot.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(clientSecretFile, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials



def downloadLatestSheets(docid,clientSecretFile):
    #Connect to google doc and get latest data

    #https://developers.google.com/sheets/quickstart/python
    credentials = get_credentials(clientSecretFile)
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = docid
    
    currentSheetName = getDatedSheet()
        
    rangeName = currentSheetName + '!A1:H'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])
    
    with open(currentSheetName+'.tsv','w') as downloadedTsv:
        if not values:
            print('No data found.')
        else:
            for row in values:
                for column in row:
                    print(column.encode('ascii', 'ignore').strip('\n\t\r'))
                    downloadedTsv.write('%s\t' % column.encode('ascii', 'ignore').strip('\n\t\r'))
                downloadedTsv.write('\n')
    downloadedTsv.close()
        
def processDownloadedSheets():
    #Read data and create reports

    
    #Loop through all .tsv files
    for thisFilename in os.listdir("./"):
        if thisFilename.endswith(".tsv"):
            print(thisFilename)
            thisFile = open(thisFilename,'r+')
            print('Parsing {}...'.format(thisFilename))
            
            allLines = re.split(r'\n',thisFile.read())
            
            #Define column headers
            headerProcessed = False
            columnCount = len(allLines[0].split('\t'))
            print(columnCount)
            if columnCount>5:
                #Typical format
                pocColumn = 5
                songColumn = 6
            else:
                #Revert to the last column if not enough columns
                pocColumn = columnCount-1
                songColumn = columnCount-1
            
            for line in allLines:
                allFields = re.split(r'\t',line)
                datestr = re.match(r'\d+/\d+/\d+',allFields[DATECOLUMN])
                print(allFields[DATECOLUMN])
                if datestr and headerProcessed and len(allFields)>songColumn:
                    datestr = datestr.group(0)
                    date = datetime.strptime(re.sub(r'\s.*','',datestr), '%m/%d/%Y').date()
                    poc = allFields[pocColumn]
                    if VERBOSE:
                        print('POC: {}'.format(poc))
                        print(len(allFields))
                    rawSongString = allFields[songColumn]
                    if VERBOSE:
                        print('Raw Song String: {}'.format(rawSongString))
                    
                    ServiceDate(date, poc, rawSongString)

                else:
                    #parsing header
                    for idx, field in enumerate(allFields):
                        print(field)
                        if 'Hymn' in field:
                            songColumn = idx
                        elif 'Musician' in field:
                            pocColumn = idx
                    headerProcessed = True
                    print('Parsed header line: {}'.format(line))
            thisFile.close()
    
    ##if no song number:
    ##ideally, would wait till the end of loop to check for numberless
    ##look up song number using the available title
    
    #Assign most frequently used titles to correct for typos
    for song in Song.songs_dict.values():
        titleMaxUseCount = 0
        maxUseTitle = ''
        for titleOption in SongTitle.songTitles_dict.values():
            if titleOption.title and titleOption.number == song.number and titleOption.useCount > titleMaxUseCount:
                titleMaxUseCount = titleOption.useCount
                maxUseTitle = titleOption.title
                song.title = maxUseTitle
                if VERBOSE:
                    print('New max use title for song {}: {}'.format(song.number,maxUseTitle))
    
    #Determine most current song date
    newestSongDate = datetime(1, 1, 1).date()
    for song in Song.songs_dict.values():
            sortedDateList = sorted(song.dates)
            lastDate = sortedDateList[-1]
            if lastDate > newestSongDate:
                newestSongDate = lastDate
        
    #write results
    with open(OUTPUT_FILENAME,'w') as report:
        nineWeeksAgo = date.today() + timedelta(days=-63)
        oneYearAgo = date.today() + timedelta(days=-365)
        report.write('Number of song\tSong title\tDate first used\tDate last used\t# Uses from {} to {}\t# Uses in the last 52 weeks\tTotal # uses\t# Appearing First\t# Appearing Middle\t# Appearing Last\tMonth Most Commonly Used\tSeason Most Commonly Used\tSongbot was here: {}'.format(nineWeeksAgo.strftime('%m/%d/%Y'),newestSongDate.strftime('%m/%d/%Y'),date.today().strftime('%m/%d/%Y')))
    
        for song in sorted(Song.songs_dict.values(), key=lambda x: len(x.dates), reverse=True):
            sortedDateList = sorted(song.dates)
            firstDate = sortedDateList[0]
            lastDate = sortedDateList[-1]
            last9WksCount = sum(1 for i in sortedDateList if i > nineWeeksAgo)
            last52WksCount = sum(1 for i in sortedDateList if i > oneYearAgo)
            
            #Count most common month
            monthCount = [0] * 12
            for date in sortedDateList:
                monthCount[date.month-1] = monthCount[date.month-1] + 1
            maxMonthlyValue = max(monthCount)
            maxMonth = monthCount.index(maxMonthlyValue) + 1
            
            seasonCount = [0] * 4
            for date in sortedDateList:
                seasonCount[get_season(date)] = seasonCount[get_season(date)] + 1
            maxSeasonValue = max(seasonCount)
            maxSeason = seasonList[seasonCount.index(maxSeasonValue)]
            
            report.write('\n{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(song.number,
                         song.title,
                         firstDate.isoformat(),
                         lastDate.isoformat(),
                         last9WksCount,
                         last52WksCount,
                         len(sortedDateList),
                         song.firstCount,
                         song.middleCount,
                         song.lastCount,
                         maxMonth,
                         maxSeason))
    report.close()
    
    #Write log for debugging
    with open(LOG_FILENAME,'w') as log:
        log.write('Song Number\tUnique Title\tUse Count\tTitle Match Count')
        for songTitle in sorted(SongTitle.songTitles_dict.values(), key=lambda x: x.number):
            log.write('\n{}\t{}\t{}\t{}'.format(songTitle.number,songTitle.title,songTitle.useCount,songTitle.matchCount))
        log.write('\n\nDate of Unmatched Songs\tRaw Song String')
        for serviceDate in ServiceDate.serviceDate_dict.values():
            if not serviceDate.parsed:
                log.write('\n{}\t{}'.format(serviceDate.date.isoformat(),serviceDate.rawSongString))
    log.close()
        
    print('Complete.')

def uploadProcessedSheets(docid,clientSecretFile):
    #Updates Songlist sheet in the google doc

    reportSheetName = 'SongList'
    
    credentials = get_credentials(clientSecretFile)
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    rangeData = []
    with open(OUTPUT_FILENAME,'r') as report:
        for lineidx,line in enumerate(report):
            rangeData.append(line.split('\t'))
    report.close()
    print(len(rangeData))
    rangeName = '{}!A{}:M'.format(reportSheetName,1)
    
    myBody = {u'range': rangeName, u'values': rangeData, u'majorDimension': u'ROWS'}
    rangeOutput = rangeName.encode('utf-8')
    result = service.spreadsheets().values().update( 
        spreadsheetId=docid, range=rangeOutput, valueInputOption='USER_ENTERED', body=myBody 
        ).execute()    
    return
    
def main():
    if DOWNLOAD_AND_UPDATE:
        (docid,clientSecretFile) = getAccountDetails()
        downloadLatestSheets(docid,clientSecretFile)

    processDownloadedSheets()
    
    if DOWNLOAD_AND_UPDATE:
        uploadProcessedSheets(docid,clientSecretFile)

if __name__ == '__main__':
    main()
