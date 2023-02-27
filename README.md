# CritiqueMeta
This projects obtains videogames related data, in order to output interesting visualization and detect biases. We will gather data from metacritic.

### 1 - Data scraping
The first step is to get the data from metacritic website. 
Game information and reviews scores are scraped for the following platforms
- PlayStation 4
- Playstation 5
- Xbox One
- Xbox Series
- 3DS
- Wii u
- Switch
We are not taking the summary of the game as we are not going to use it.
I tried getting data from the following platforms:
- ps3
- xbox 360
- PC
but some issues with user reviews led me to simply abandon. Anyway, we have plenty of recent data to play with!

### 2 - Data cleaning
Once raw data is available, it's time to clean.
In particular, we'll make sure to make the date readable, harmonize the scores between users and critics and removing rows with empty values.

### 3 - Data analysis
To be built