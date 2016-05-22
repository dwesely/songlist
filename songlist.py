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
from datetime import datetime
from datetime import timedelta
import os

#Header on the date column is inconsistent, but it is consistently in the first column
DATECOLUMN = 0

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
        #TODO: if there are spelling variations in title, maybe keep a list of referenced titles, sort, and take the median?
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
    if number not in Song.songs_dict:
        songObj = Song(number, title)
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
        
        SongTitle.songTitles_dict[title] = self
def getSongNumber(title):
    if title not in SongTitle.songTitles_dict:
        print('Song title "{}" not found in list.'.format(title))
        songTitleObj = []
    else:
        songTitleObj = SongTitle.songTitles_dict.get(title)
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
        if not self.rawSongString:
            print('No raw song string for date {}'.format(self.date.isoformat()))
        else:
            
            #Cleaning
            cleanedSongString = self.rawSongString
            
            ##remove preambles (e.g. "Tentative:")
            numbersFound = re.findall(r'\d+',cleanedSongString)
            #if no semicolon:
            if len(numbersFound) > 1 and not cleanedSongString.find(';')>0:
                #could just be a single song
                print(re.sub(r'[_]*\W+(\d+)',';{\1}',cleanedSongString))
                cleanedSongString = re.sub(r'[_]*\W+(\d+)',';{\1}',cleanedSongString)
                #identify if digits are in front or in back of the titles (find first digit, count index, if <5, digits are in front)
                #replace non-word characters in front/behind the digits with semicolons
                #r('(\W+\d+)')
            
            #split recorded songs (typically semicolon or comma separating multiple entries)
            individualSongs = cleanedSongString.split(';')
            print(individualSongs)
            
            for songStr in individualSongs:
                #parse song title and number
                #song number first:
                numberTitle = re.search(r'\D*(\d+)\W*(\D+[^;]+)',songStr)
                if not numberTitle:
                    print('Song {} not parsed.'.format(songStr))
                    return
                elif not numberTitle.group(2).strip(' \t\n\r'):
                    print('No title for song {}'.format(numberTitle.group(1)))
                else:
                    songNumber = numberTitle.group(1).strip(' \t\n\r')
                    songTitle  = numberTitle.group(2).strip(' \t\n\r')
                    
                    #save song
                    songObj = getSong(songNumber, songTitle)
                    if songObj:
                        songObj.add_date(self.date)

                    #record placement (first/middle/last)
            
            self.parsed = True
            print('Successfully parsed {}'.format(cleanedSongString))
        
def getServiceDate(date):
    if date not in ServiceDate.serviceDate_dict:
        print('Service Date "{}" not found in list.'.format(date))
        serviceDateObj = []
    else:
        serviceDateObj = ServiceDate.serviceDate_dict.get(date)
    return serviceDateObj
    
#File management

#Initialize variables

#Loop through all .tsv files
for thisFilename in os.listdir("./"):
    if thisFilename.endswith(".tsv"):
        print(thisFilename)
        thisFile = open(thisFilename,'r+')
        print('Parsing {}...'.format(thisFilename))
        
        allLines = re.split(r'\n',thisFile.read())
        
        #Define column headers - input format is pretty consistent, so I don't plan to write a parser for the header
        pocColumn = 5
        songColumn = 6
        
        headerProcessed = False
        
        for line in allLines:
            allFields = re.split(r'\t',line)
            datestr = re.match(r'\d+/\d+/\d+',allFields[DATECOLUMN])
            #print(allFields[DATECOLUMN])
            if datestr and headerProcessed:
                datestr = datestr.group(0)
                date = datetime.strptime(re.sub(r'\s.*','',datestr), '%m/%d/%Y').date()
                        
                
                poc = allFields[pocColumn]
                #print(poc)
                
                rawSongString = allFields[songColumn]
                print(rawSongString)
                
                ServiceDate(date, poc, rawSongString)
            else:
                for idx, field in enumerate(allFields):
                    if field == 'Hymn numbers':
                        songColumn = idx
                    elif field == 'Musicians / choir?':
                        pocColumn = idx
                headerProcessed = True
                print('Skipped line: {}'.format(line))
        thisFile.close()

##if no song number:
##ideally, would wait till the end of loop to check for numberless
##look up song number using the available title



#write to report:
#Number of song,Song title,Date first used,Date last used, ...
## Uses in the last 9 weeks,# Uses in the last 52 weeks,Total # uses, ...
## Appearing First,# Appearing Middle,# Appearing Last
outputFilename = 'songlistReport.txt'

#TODO: datestamp the songlist

with open(outputFilename,'w') as report:
    report.write('Number of song\tSong title\tDate first used\tDate last used\t# Uses in the last 9 weeks\t# Uses in the last 52 weeks\tTotal # uses\t# Appearing First\t# Appearing Middle\t# Appearing Last')
    for song in Song.songs_dict.values():
        sortedDateList = sorted(song.dates)
        firstDate = sortedDateList[0]
        lastDate = sortedDateList[-1]
        last9WksCount = sum(1 for i in sortedDateList if i > date.today() + timedelta(days=-63))
        last52WksCount = sum(1 for i in sortedDateList if i > date.today() + timedelta(days=-365))

        report.write('\n{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(song.number,
                     song.title,
                     firstDate.isoformat(),
                     lastDate.isoformat(),
                     last9WksCount,
                     last52WksCount,
                     len(sortedDateList),
                     song.firstCount,
                     song.middleCount,
                     song.lastCount
))
report.close()
print('Complete.')
