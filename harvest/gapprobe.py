import json, time, urllib.parse, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
YRS = ' OR '.join(str(y) for y in range(1984, 2005))
BASE = 'mediatype:movies AND (year:[1984 TO 2004] OR date:[1984-01-01 TO 2004-12-31] OR title:(' + YRS + '))'
P = [
 ('morning network shows', 'title:("today show" OR "good morning america" OR "cbs this morning" OR "the early show" OR "cbs morning news")'),
 ('weather channel', 'title:("weather channel" OR weatherstar OR "local forecast")'),
 ('cooking', 'title:("frugal gourmet" OR "julia child" OR "yan can cook" OR "great chefs" OR emeril OR "cooking show" OR "galloping gourmet" OR "justin wilson")'),
 ('home and garden', 'title:("this old house" OR "bob vila" OR hometime OR "victory garden" OR "new yankee workshop" OR "joy of painting")'),
 ('classic reruns', 'title:("nick at nite" OR "tv land" OR "i love lucy" OR "brady bunch" OR "gilligan\'s island" OR "andy griffith" OR "leave it to beaver" OR bewitched OR "happy days")'),
 ('religious', 'title:("700 club" OR "pTL club" OR "jimmy swaggart" OR "oral roberts" OR "robert schuller" OR "hour of power" OR "jerry falwell" OR "old time gospel hour" OR televangelist OR "trinity broadcasting" OR "ernest angley" OR "robert tilton")'),
 ('home shopping', 'title:(qvc OR hsn OR "home shopping network" OR "home shopping club" OR "shop at home")'),
 ('infomercials', 'title:(infomercial OR infomercials OR "paid programming")'),
 ('court shows', 'title:("people\'s court" OR "judge judy" OR "divorce court" OR "judge wapner" OR "superior court" OR "judge joe brown" OR "judge mathis")'),
 ('tabloid reality', 'title:(cops OR "rescue 911" OR "america\'s most wanted" OR "real stories of the highway patrol" OR "top cops" OR "real tv" OR "world\'s wildest police")'),
 ('true crime mystery', 'title:("unsolved mysteries" OR "sightings" OR "in search of" OR "encounters" OR "the extraordinary" OR "ripley\'s believe it or not" OR "that\'s incredible")'),
 ('pbs kids', 'title:("sesame street" OR "mister rogers" OR "reading rainbow" OR "square one" OR "3-2-1 contact" OR ghostwriter OR "electric company" OR wishbone OR "lamb chop")'),
 ('teen sitcoms', 'title:("saved by the bell" OR "california dreams" OR "hang time" OR "city guys" OR "tnbc" OR "sweet valley high" OR "clarissa explains")'),
 ('sketch standup', 'title:("evening at the improv" OR "comic strip live" OR "stand-up spotlight" OR "comedy central presents" OR "hbo comedy" OR "one night stand" OR "young comedians" OR "in living color" OR "mad tv" OR "kids in the hall")'),
 ('awards shows', 'title:("academy awards" OR oscars OR "emmy awards" OR "grammy awards" OR "golden globe" OR "american music awards" OR "people\'s choice" OR "mtv video music awards" OR "tony awards" OR "country music awards")'),
 ('parades', 'title:("thanksgiving day parade" OR "rose parade" OR "tournament of roses" OR "christmas parade" OR "macy\'s parade" OR "disney parade" OR "easter parade")'),
 ('pageants', 'title:("miss america" OR "miss usa" OR "miss universe" OR "miss teen usa" OR pageant)'),
 ('telethons', 'title:(telethon)'),
 ('variety specials', 'title:("variety special" OR "tv special" OR "bob hope" OR "circus of the stars" OR "night of 100 stars" OR "battle of the network stars" OR "anniversary special")'),
 ('miniseries tv movies', 'title:(miniseries OR "mini-series" OR "tv movie" OR "movie of the week" OR "made for tv")'),
 ('country nashville', 'title:("nashville now" OR "hee haw" OR "grand ole opry" OR "crook and chase" OR "tnn" OR "nashville network" OR "austin city limits" OR "country music television" OR "cmt")'),
 ('fishing hunting outdoors', 'title:("bill dance" OR "fishing with" OR "in-fisherman" OR "bassmasters" OR "hank parker" OR "american sportsman" OR "outdoor life" OR "babe winkelman" OR "fishing show" OR "hunting show")'),
 ('car motor shows', 'title:(motorweek OR "shadetree mechanic" OR "truckin usa" OR "road test magazine" OR "car and driver" OR "horsepower tv" OR "trucks!" OR "motor trend")'),
 ('exercise aerobics', 'title:(aerobics OR "bodies in motion" OR "20 minute workout" OR "body by jake" OR "getting fit" OR "jane fonda" OR "richard simmons" OR "body electric" OR "fitness pros" OR "basic training")'),
 ('travel shows', 'title:("travel channel" OR "rick steves" OR "lonely planet" OR "travel guide" OR "great railway journeys" OR "travels in europe" OR "world of travel")'),
 ('nature docs', 'title:("wild kingdom" OR "national geographic" OR "wild america" OR "nature" OR "wild discovery" OR "world of survival" OR "lorne greene\'s new wilderness")'),
 ('science shows', 'title:(nova OR "beyond 2000" OR "newton\'s apple" OR "scientific american frontiers" OR "bill nye" OR "beakman" OR "mr. wizard" OR "cosmos")'),
 ('history war docs', 'title:("history channel" OR "world at war" OR "victory at sea" OR "civil war journal" OR "modern marvels" OR "in search of history" OR "our century" OR "wings" OR "tales of the gun")'),
 ('biography', 'title:("a&e biography" OR "biography:" OR "biography -" OR "intimate portrait" OR "e! true hollywood story" OR "behind the music")'),
 ('business financial', 'title:("wall street week" OR "nightly business report" OR moneyline OR cnbc OR "financial news network" OR "fnn" OR "adam smith\'s money world" OR "business day")'),
 ('political sunday', 'title:("meet the press" OR "face the nation" OR "this week with david brinkley" OR "mclaughlin group" OR crossfire OR "firing line" OR "capital gang" OR "washington week")'),
 ('overnight news', 'title:("nbc news overnight" OR "cbs news nightwatch" OR "world news now" OR "nbc nightside" OR "up to the minute" OR "abc news overnight")'),
 ('adult animation 90s', 'title:("beavis and butt-head" OR "liquid television" OR "aeon flux" OR "the maxx" OR "duckman" OR "the critic" OR "dr. katz" OR "space ghost coast to coast" OR "the head" OR daria)'),
 ('mtv non video', 'title:("remote control" OR "real world" OR "road rules" OR "singled out" OR "the state" OR "house of style" OR "mtv news" OR "week in rock" OR "mtv sports" OR "the grind" OR "total request live" OR "mtv spring break")'),
 ('vh1 shows', 'title:("pop-up video" OR "pop up video" OR "behind the music" OR "storytellers" OR "vh1 to one" OR "my generation" OR "where are they now" OR "i love the 80s" OR "vh1 divas")'),
 ('bet shows', 'title:("video soul" OR "rap city" OR "comicview" OR "comic view" OR "teen summit" OR "bobby jones gospel" OR "bet jazz" OR "planet groove" OR "106 & park" OR "midnight love")'),
 ('public access oddities', 'title:("public access" OR "cable access" OR "community access" OR "access tv")'),
 ('horror hosts kids hosts', 'title:(elvira OR svengoolie OR "commander usa" OR "joe bob" OR "monstervision" OR "grampa" OR "zacherley" OR "count gore" OR "dr. paul bearer" OR "horror host" OR "bozo" OR "romper room" OR "captain kangaroo" OR "wonderama")'),
 ('high school local sports', 'title:("high school football" OR "high school basketball" OR "friday night football" OR "game of the week" OR "state championship")'),
 ('bowling billiards filler sports', 'title:(bowling OR "pro bowlers tour" OR pba OR billiards OR "trick shot" OR "world\'s strongest man" OR "american gladiators" OR "arm wrestling" OR "lumberjack" OR "poker")'),
 ('rodeo monster trucks derby', 'title:(rodeo OR "monster truck" OR "monster trucks" OR "monster jam" OR "roller derby" OR "rollergames" OR "tractor pull" OR "demolition derby" OR "tnt motorsports" OR "ushra")'),
 ('wrestling wwf', 'title:(wwf OR "world wrestling federation")'),
 ('wrestling wcw nwa', 'title:(wcw OR nwa OR "world championship wrestling")'),
 ('wrestling awa wccw ecw other', 'title:(awa OR wccw OR "world class championship" OR ecw OR uswa OR gwf OR "smoky mountain wrestling" OR glow)'),
 ('telecourses instructional', 'title:(telecourse OR "annenberg" OR "the mechanical universe" OR "french in action" OR "destinos" OR "economics usa" OR "college algebra" OR "learn to read" OR "ged on tv" OR "the write course")'),
 ('halloween specials', 'title:(halloween OR "great pumpkin" OR "garfield\'s halloween")'),
 ('thanksgiving specials', 'title:(thanksgiving)'),
 ('christmas specials', 'title:(christmas)'),
 ('easter specials', 'title:(easter)'),
 ('valentine specials', 'title:(valentine OR "valentine\'s")'),
 ('4th of july', 'title:("fourth of july" OR "4th of july" OR "independence day" OR "a capitol fourth" OR "macy\'s fireworks")'),
 ('new years eve', 'title:("new year\'s eve" OR "new year\'s rockin" OR "rockin\' eve" OR "new years eve")'),
 ('election night', 'title:("election night" OR "election coverage" OR "decision 88" OR "decision 92" OR "campaign 92" OR "vote 96" OR "election 2000" OR "debate")'),
 ('major news events', 'title:(challenger OR "gulf war" OR "desert storm" OR "berlin wall" OR "o.j. simpson" OR "oj simpson" OR "oklahoma city" OR "princess diana" OR "september 11" OR "9/11" OR columbine OR "la riots" OR "hurricane andrew" OR "loma prieta")'),
 ('late night talk', 'title:("tonight show" OR letterman OR "late night with" OR arsenio OR "conan o\'brien")'),
 ('daytime talk', 'title:(donahue OR oprah OR geraldo OR "sally jessy" OR "jerry springer" OR "ricki lake" OR "jenny jones" OR montel OR maury)'),
 ('soaps nbc', 'title:("days of our lives" OR "another world" OR "santa barbara" OR "sunset beach" OR passions)'),
 ('soaps cbs', 'title:("young and the restless" OR "bold and the beautiful" OR "as the world turns" OR "guiding light")'),
 ('soaps abc', 'title:("general hospital" OR "all my children" OR "one life to live" OR "ryan\'s hope" OR loving)'),
 ('entertainment magazines', 'title:("entertainment tonight" OR "a current affair" OR "inside edition" OR "hard copy" OR "extra" OR "access hollywood" OR "e! news" OR "lifestyles of the rich")'),
 ('saturday morning blocks', 'title:("saturday morning")'),
 ('station sign-offs', 'title:("sign off" OR "sign-off" OR signoff)'),
 ('local newscasts', 'title:("eyewitness news" OR "action news" OR "news at 11" OR "news at 6" OR "news at 10" OR newscast)'),
 ('game shows', 'title:("wheel of fortune" OR jeopardy OR "price is right" OR "family feud" OR "press your luck")'),
 ('kung fu creature feature movies', 'title:("kung fu theater" OR "black belt theater" OR "creature feature" OR "chiller theater" OR "up all night" OR "late movie" OR "late late show")'),
 ('c-span style govt', 'title:(c-span OR cspan)'),
 ('sports talk highlight shows', 'title:(sportscenter OR "this week in baseball" OR "nfl films" OR "inside the nfl" OR "george michael sports machine" OR "nba inside stuff" OR "wide world of sports" OR "sports reporters")'),
]
def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            time.sleep(3 * (k + 1))
    return None
print('GAPPROBE label | era_count | per-year 1984..2004')
for lab, q in P:
    u = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': '(' + q + ') AND ' + BASE, 'rows': 0, 'output': 'json', 'facet.field': 'year', 'facet': 'on'})
    j = get(u)
    n = (j or {}).get('response', {}).get('numFound', -1)
    u2 = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': '(' + q + ') AND mediatype:movies AND year:[1984 TO 2004]', 'rows': 0, 'output': 'json'})
    ys = []
    for a, b in ((1984, 1987), (1988, 1991), (1992, 1995), (1996, 1999), (2000, 2004)):
        j2 = get('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({'q': '(' + q + ') AND mediatype:movies AND year:[%d TO %d]' % (a, b), 'rows': 0, 'output': 'json'}))
        ys.append((j2 or {}).get('response', {}).get('numFound', -1))
    print('GAPPROBE', lab, '|', n, '|', ' '.join(str(x) for x in ys), flush=True)
    time.sleep(0.5)
