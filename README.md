# Can a market timing strategy outperform the monthly savings plan for index investing?
I have been investing into ETFs (in particular the MSCI World ETF) for 2 years now and and invested a lot about 2 years ago when the prices were relatively low. As of today (Feb 2020) my MSCI World ETF value is about 30% higher than 2 years ago. Since September 2019 the prices have increased a lot. This made me reluctant to invest in the past 6 months and made me wait for better times with lower prices. But actually the prices kept increasing for months. I would need a drop of 20% for the MSCI World to get to a price that I rejected months ago because it seemed to high to invest at that time. This makes me overthink my strategy, whether it's really a good idea to wait for a good time to invest versus just doing it on a monthly basis no matter what's the current price. 

This is the motivation for a comparison between a monthly savings plan and a market timing strategy. The market timing strategy resembles my investment strategy of the past 2 years. It invests when the drop in price is high. 

* The monthly savings plan invests every month on the first business day of the month the full amount of cash.
* The market timing strategy invests depending on the drop in price compared to the highest price peak within the last 6 months. I chose 6 months since I usually look back 6 months to differentiate between a good or bad time to invest. Further details regarding this strategy will follow in the notebook in its respective section. 

The investment horizon is 20 years because this is my trageted horizon. To achieve a representative result which can be averaged over as many 20 year horizons as possible I require an index with a long history of daily figures. For the MSCI World Index I found daily figures only for the last couple of years. The required figures are available for the S&P 500 since 1927 making 72 20 year slices possible until end of 2019. This is why this index is chosen as basis for this comparison. But only data since 1950 is considered, since the years after 1950 seem more relevant to our current market situation.  

The monthly savings are assumed to be 1000 Dollar. So each month it's possible to invest 1000 Dollar for the savings plan as well as the market timing strategy.

# Spoiler alert: The monthly savings plan can't be outperformed with my strategy
The market timing strategy and even a hybrid between the monthly investment and the market timing strategy can't outperform the monthly savings plan.

But I'm just some Data Scientist with little experience in finance playing around with ideas. My market timing strategy is probably far from perfect, but it does resemble my investment strategy from the past two years and I imagine that many more are investing in that way. I hope to help these people, just like I helped myself, to overcome the burden of trying to find the best time to invest and choose the simple and "boring" way of just investing on a monthly basis. 

# Summary of parameters used for this comparison
monthly_savings = 1000 Dollar
horizon_length = 20 years
etf_idx = '^GSPC' (S&P 500)