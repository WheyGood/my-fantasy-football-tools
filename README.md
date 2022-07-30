# Fantasy Football Python Information Tools

Fantasy Football Analysis Tools to help make informed draft and trade decisions


## Authors

- [@WheyGood (Matt S)](https://www.https://github.com/WheyGood)

## FantasyPros Live Scrape Sleeper Finder

Value over replacement based sleeper ranking program.  Print sleepers to screen to determine 
who may be a value pick during your drafts!  Make sure to run near draft day for best results.


### Calculations
Sleepers are determined by subtracting VOR rank values by ADP rank values

VOR is determined by finding the projected fantasy point totals for each position at around
pick 100 and then subtracted from each players projected total fantasy points.  

Sleepers are sorted based on greatest difference between average draft position and their
value over replacement rank.







### Deployment

This program requires three command line arguments.  

First, determine the style of league you
play in, basically how many points you get per catch.  The first command line argument will simply
be a single letter.  If you play in a standard league where catches have no extra value then 
type in 's', for a half point per reception league use 'h', and for a full point per reception
league use 'p'   

The second argument is the number of members in your league.

The final argument is the total number of players in your starting lineup and on the bench.
Typically, 13 or 14 is a normal for this value. 

 ```
 python sleepers.py s 10 13
 ```


### Output Example
![](images/sleeper_args.png)
![](images/sleeper_output.png)




