# CritiqueMeta
This projects obtains videogames related data, in order to output interesting visualizations and detect biases. We will gather data from metacritic.

Direct link to the analysis page: 
https://tjubault.github.io/CritiqueMeta/data_analysis.html

### 1 - Data gatherer
The first step is to get the data from metacritic website. 

Basic Game information, critic reviews scores and user reviews scores are scraped for the following platforms
- Playstation 4
- Playstation 5
- Xbox One
- Xbox Series X (I assume that also works for Series S)
- 3DS
- Wii u
- Switch

We are not taking the summary of the game as we are not going to use it. 

I tried getting data from the following platforms:

- ps3
- xbox 360
- PC

but some issues with user reviews led me to simply abandon. Anyway, we have plenty of recent data to play with!

### 2 - Data cleanup and preparation
Once raw data is available, we make sure it is ready to be analyzed (missing values and incorrect formats). 

### 3 - Data analysis
Now it's time to make sense of that bunch of dataframes! 

Time for my beloved plotly to shine.
