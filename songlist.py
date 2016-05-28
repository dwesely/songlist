# -*- coding: utf-8 -*-
"""
Created on Fri May 20 22:03:45 2016

songlist.py

Purpose: Parse a folder full of tab-separated files containing historical information
on the use of hymns, to be used as a planning tool to reduce back-to-back usage of
hymns, but also provide a list of hymns with familiarity to be used as a baseline
repertoire.

@author: Wesely
"""

import re
from datetime import date,datetime
from datetime import timedelta
import os

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
        self.title         = title
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
        self.title         = title
        self.number        = number
        self.useCount      = 1
        
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
    if VERBOSE:
        print('Getting song titled {}'.format(title))
    if title.strip('\n\t\r '):
        if title not in SongTitle.songTitles_dict:
            if VERBOSE:
                print('Song title "{}" not found in list.'.format(title))
        elif isinstance(title, basestring):
            songTitleObj = SongTitle.songTitles_dict.get(title)
        else:
            if VERBOSE:
                print('Song title is not a string.')
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
            print('Raw string: {}'.format(rawSongString))
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
    
#File management
outputFilename = 'songlistReport.txt'
logFilename    = 'log.txt'

#Initialize variables

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
            #print(allFields[DATECOLUMN])
            if datestr and headerProcessed:
                datestr = datestr.group(0)
                date = datetime.strptime(re.sub(r'\s.*','',datestr), '%m/%d/%Y').date()
                poc = allFields[pocColumn]
                if VERBOSE:
                    print('POC: {}'.format(poc))
                
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

#write results

with open(outputFilename,'w') as report:
    report.write('Number of song\tSong title\tDate first used\tDate last used\t# Uses in the last 9 weeks\t# Uses in the last 52 weeks\tTotal # uses\t# Appearing First\t# Appearing Middle\t# Appearing Last\tMonth Most Commonly Used\tSeason Most Commonly Used')
    for song in sorted(Song.songs_dict.values(), key=lambda x: len(x.dates), reverse=True):
        sortedDateList = sorted(song.dates)
        firstDate = sortedDateList[0]
        lastDate = sortedDateList[-1]
        last9WksCount = sum(1 for i in sortedDateList if i > date.today() + timedelta(days=-63))
        last52WksCount = sum(1 for i in sortedDateList if i > date.today() + timedelta(days=-365))
        
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
with open(logFilename,'w') as log:
    log.write('Song Number\tUnique Title')
    for songTitle in sorted(SongTitle.songTitles_dict.values(), key=lambda x: x.number):
        log.write('\n{}\t{}'.format(songTitle.number,songTitle.title))
    log.write('\n\nDate of Unmatched Songs\tRaw Song String')
    for serviceDate in ServiceDate.serviceDate_dict.values():
        if not serviceDate.parsed:
            log.write('\n{}\t{}'.format(serviceDate.date.isoformat(),serviceDate.rawSongString))
log.close()
    
print('Complete.')
