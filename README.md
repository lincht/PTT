# PTT
Analysis of the largest BBS in Taiwan.

### Quick start

To scrape the latest 50 pages from the *Gossiping* board, simply run:

```shell
$ python pttscraper.py
```

The scraped data will be saved as ```Gossiping_YYMMDD.csv```, and has the following format:

| author       | alias      | title                                                 | date                | ip             | city      | country            |   ups |   downs |   comments | url                                                      |
|:-------------|:-----------|:------------------------------------------------------|:--------------------|:---------------|:----------|:-------------------|------:|--------:|-----------:|:---------------------------------------------------------|
| Tsumugifans  | 0.0        | Re: [問卦] 為什麼網軍都在PTT？                        | 2018-04-18 16:49:31 | 175.125.61.131 | Seoul     | Korea, Republic of |  1381 |      13 |        100 | https://www.ptt.cc/bbs/Gossiping/M.1524041373.A.35A.html |
| abianisbitch | 阿扁是錶子 | Re: [新聞]  發錢  蔡英文：年輕人想要80分 我做70分被罵 | 2018-04-21 12:14:51 | 97.91.21.1     | Allendale | United States      |  1279 |      89 |        122 | https://www.ptt.cc/bbs/Gossiping/M.1524284094.A.9F3.html |
| saisai9230   | 小為       | [新聞] 超狂！抵押住家打選戰　柯P：不想拿人手短        | 2018-04-14 16:18:49 | 111.243.159.33 | nan       | Taiwan             |  1139 |      66 |        277 | https://www.ptt.cc/bbs/Gossiping/M.1523693933.A.3F4.html |
| stanley20    | 蘇丹利     | [問卦] google drive 怎麼找影片最快？                  | 2018-04-21 18:15:18 | 58.114.212.121 | nan       | Taiwan             |   984 |      25 |         66 | https://www.ptt.cc/bbs/Gossiping/M.1524305721.A.CA2.html |
| hahaha0204   | 哈哈哈     | [爆卦] Avicii 過世了                                  | 2018-04-21 01:37:35 | 1.171.192.69   | nan       | Taiwan             |   951 |     100 |        213 | https://www.ptt.cc/bbs/Gossiping/M.1524245858.A.F5B.html |

_**\*Note that currently the main content of articles, including push comments, is not scraped.**_

### Optional flags

You can scrape any number of pages from any board you like, by specifying the following flag(s):

| Flag | Description                 |
|:-----|:----------------------------|
| -b   | board name (case-sensitive) |
| -p   | number of pages to scrape   |
| -f   | output file name            |

Sample command:

```shell
$ python pttscraper.py -b Stock -p 100 -f output.csv
```

If not passed, default behavior is to scrape 50 pages from the *Gossiping* board.