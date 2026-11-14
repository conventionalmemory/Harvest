import json, gzip, os, re, sys, time, random, collections, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (retrotv-sources harvester)'}
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, '..', 'catalog'); os.makedirs(OUT, exist_ok=True)
THREADS = int(os.environ.get('THREADS', '16'))
import glob
have = set()
for _p in glob.glob(os.path.join(OUT, '*.json.gz')):
    if os.path.basename(_p) in ('schoolage.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'ads.json.gz'): continue
    try:
        for _x in json.load(gzip.open(_p, 'rt', encoding='utf-8')):
            if isinstance(_x, dict) and 'i' in _x: have.add(_x['i'])
            elif isinstance(_x, list) and _x and isinstance(_x[0], str): have.add(_x[0])
    except Exception as _e: print('skip', _p, _e)
print('existing', len(have), flush=True)
S = [
('ycdtotv', 1986, ["you can't do that on television", "you cant do that on television"], None),
('mrwizard', 1986, ["mr. wizard's world", "mr wizard's world", "mr wizards world", "mr. wizard"], None),
('doubledare', 1988, ["double dare", "family double dare", "super sloppy double dare"], r"double dare"),
('finderskeepers', 1988, ["finders keepers"], r"nick|game ?show|episode|\b198[789]\b|wesley|toffler"),
('thinkfast', 1989, ["think fast"], r"nick|game ?show|\b19(89|90|91)\b"),
('makethegrade', 1990, ["make the grade"], r"nick|game ?show|episode|\b19(89|90|91)\b"),
('getthepicture', 1991, ["get the picture"], r"nick|game ?show|episode|\b199[1-3]\b"),
('whatwouldyoudo', 1992, ["what would you do"], r"nick|marc summers|\b199[1-3]\b"),
('wildcrazykids', 1991, ["wild & crazy kids", "wild and crazy kids"], None),
('nickarcade', 1992, ["nick arcade", "nickelodeon arcade"], None),
('guts', 1993, ["nickelodeon guts", "global guts", "nick guts", "guts"], r"nickelodeon|\bnick\b|o'malley|aggro crag|global guts|mo quirk"),
('hiddentemple', 1994, ["legends of the hidden temple"], None),
('figureitout', 1998, ["figure it out"], r"nick|summer sanders|episode|\b199[789]\b|season"),
('heydude', 1990, ["hey dude"], r"nick|episode|season|s0?\d|\b(1989|199[01])\b|series"),
('saluteyourshorts', 1991, ["salute your shorts"], None),
('welcomefreshmen', 1992, ["welcome freshmen"], None),
('clarissa', 1992, ["clarissa explains it all"], None),
('petepete', 1994, ["pete & pete", "pete and pete"], None),
('afraiddark', 1993, ["are you afraid of the dark"], None),
('alexmack', 1995, ["secret world of alex mack", "alex mack"], None),
('allthat', 1996, ["all that"], r"^(nickelodeon'?s? )?all that\b.*(nick|season|episode|s0?\d|\b(199[4-9]|200[0-4])\b)|nickelodeon.*all that|snick"),
('kenankel', 1997, ["kenan & kel", "kenan and kel"], None),
('amandashow', 2000, ["the amanda show", "amanda show"], None),
('spacecases', 1996, ["space cases"], None),
('mybrotherandme', 1994, ["my brother and me"], None),
('roundhouse', 1993, ["roundhouse"], r"nick|snick|\b199[2-6]\b.*(episode|season)|episode.*roundhouse|roundhouse (s0?\d|season|episode)"),
('weinerville', 1994, ["weinerville"], None),
('nicknews', 1994, ["nick news"], None),
('allenstrange', 1998, ["journey of allen strange", "allen strange"], None),
('shelbywoo', 1997, ["shelby woo"], None),
('cousinskeeter', 1999, ["cousin skeeter"], None),
('eddiemcdowd', 2000, ["100 deeds for eddie mcdowd", "eddie mcdowd"], None),
('caitlinsway', 2000, ["caitlin's way", "caitlins way"], None),
('brothersgarcia', 2001, ["brothers garcia"], None),
('drakejosh', 2004, ["drake & josh", "drake and josh"], r"2004|season 1|s01|pilot"),
('neds', 2004, ["ned's declassified"], r"2004|season 1|s01|pilot"),
('snick', 1994, ["snick"], r"\bsnick\b"),
('nickblock', 1993, ["nickelodeon"], r"nickelodeon.*(\b(198[4-9]|199\d|200[0-4])\b).*(commercials|recording|vhs|broadcast|aircheck|block|tape)|(commercials|recording|vhs|broadcast|aircheck|block|tape).*nickelodeon.*\b(198[4-9]|199\d|200[0-4])\b"),
('kidsinc', 1987, ["kids incorporated", "kids inc"], None),
('mmc', 1991, ["mickey mouse club", "all new mickey mouse club", "the mmc"], r"mickey mouse club|\bmmc\b"),
('mousterpiece', 1984, ["mousterpiece theater"], None),
('dangerbay', 1987, ["danger bay"], None),
('babysitters', 1990, ["baby-sitters club", "babysitters club", "baby sitters club"], None),
('wonderland', 1993, ["adventures in wonderland"], None),
('flashforward', 1996, ["flash forward"], r"disney|\b199[5-7]\b|tucker|becca"),
('jettjackson', 1999, ["jett jackson"], None),
('soweird', 1999, ["so weird"], r"disney|season|episode|s0?\d|\b(1999|200[01])\b|fi phillips|series"),
('evenstevens', 2001, ["even stevens"], None),
('lizzie', 2002, ["lizzie mcguire"], None),
('raven', 2003, ["that's so raven", "thats so raven"], r"200[34]|season 1|season 2|s0[12]"),
('zoog', 2000, ["zoog disney", "vault disney"], None),
('dcom', 1999, ["disney channel original movie", "disney channel premiere film", "disney channel premiere"], None),
('disneychan', 1992, ["disney channel"], r"disney channel.*(\b(198[4-9]|199\d|200[0-4])\b).*(commercials|recording|vhs|broadcast|aircheck|block|tape|promos)|(commercials|recording|vhs|broadcast|aircheck|block|tape).*disney channel.*\b(198[4-9]|199\d|200[0-4])\b"),
('321contact', 1985, ["3-2-1 contact", "3 2 1 contact", "321 contact"], None),
('squareone', 1988, ["square one tv", "square one television", "mathnet"], None),
('ghostwriter', 1993, ["ghostwriter", "ghost writer"], r"pbs|ctw|children's television workshop|episode|season|s0?\d|\b199[2-5]\b|\barc\b|part \d|who burned|ghost story|to catch a creep|into the comics|get the message|building bridges|over a barrel"),
('carmenworld', 1992, ["where in the world is carmen sandiego"], None),
('carmentime', 1997, ["where in time is carmen sandiego"], None),
('carmenearth', 1995, ["where on earth is carmen sandiego"], None),
('billnye', 1995, ["bill nye the science guy", "bill nye"], r"science guy|episode|s0?\d|season"),
('beakman', 1994, ["beakman's world", "beakmans world"], None),
('magicschoolbus', 1996, ["magic school bus"], None),
('wishbone', 1996, ["wishbone"], r"pbs|episode|season|s0?\d|\b199[5-9]\b|dog|vhs"),
('kratts', 1996, ["kratts' creatures", "kratts creatures", "kratt's creatures"], None),
('zoom', 1999, ["zoom"], r"\bzoom\b.*(pbs|wgbh|199[89]|200[0-4]|season|episode)|pbs.*\bzoom\b"),
('newtonsapple', 1990, ["newton's apple", "newtons apple"], None),
('readingrainbow', 1990, ["reading rainbow"], None),
('longago', 1989, ["long ago and far away", "long ago & far away"], None),
('wonderworks', 1987, ["wonderworks"], None),
('degrassi', 1988, ["degrassi junior high", "degrassi jr high", "degrassi high", "kids of degrassi street"], None),
('kidsworld', 1985, ["kidsworld"], None),
('mimi', 1985, ["voyage of the mimi"], None),
('cyberchase', 2002, ["cyberchase"], r"200[2-4]|season [1-3]\b|s0[1-3]"),
('libertyskids', 2002, ["liberty's kids", "libertys kids"], None),
('arthur', 1998, ["arthur"], r"^(?!.*(square knights|king arthur|bergeron))(pbs )?(kids )?arthur\b.*(pbs|season|episode|s0?\d|vhs|\b(199[6-9]|200[0-4])\b)|arthur's (eyes|birthday|pet|lost|teacher|baby|chicken|family|tooth|new|first|perfect|tv|computer|famous|missing)"),
('zoboomafoo', 2000, ["zoboomafoo"], None),
('peewee', 1988, ["pee-wee's playhouse", "pee wee's playhouse", "peewee's playhouse", "pee-wees playhouse"], None),
('savedbythebell', 1991, ["saved by the bell", "good morning, miss bliss", "good morning miss bliss"], None),
('tnbc', 1996, ["california dreams", "hang time", "city guys", "one world", "tnbc", "running the halls", "name your adventure", "nba inside stuff"], r"california dreams|hang time|city guys|tnbc|running the halls|name your adventure|inside stuff|one world.*(nbc|tnbc|episode|season)"),
('landofthelost', 1992, ["land of the lost"], r"199[1-3]|1991|abc|tom porter"),
('billted', 1991, ["bill & ted's excellent adventures", "bill and ted's excellent adventures"], None),
('beetleborgs', 1997, ["beetleborgs"], None),
('goosebumps', 1996, ["goosebumps"], r"episode|season|s0?\d|tv|series|fox|\b199[5-8]\b|vhs"),
('eerie', 1992, ["eerie, indiana", "eerie indiana"], None),
('animorphs', 1999, ["animorphs"], r"episode|season|s0?\d|tv|series|nick|\b(1998|1999|2000)\b"),
('shirttales', 1984, ["shirt tales"], None),
('weekendspecial', 1987, ["abc weekend special", "abc weekend specials", "o.g. readmore", "og readmore"], None),
('storybreak', 1986, ["cbs storybreak"], None),
('schoolbreak', 1988, ["cbs schoolbreak special", "schoolbreak special", "cbs schoolbreak", "schoolbreak"], None),
('afterschool', 1987, ["abc afterschool special", "afterschool special", "after school special"], None),
('specialtreat', 1985, ["nbc special treat", "special treat"], r"nbc"),
('kidsarepeople', 1984, ["kids are people too"], None),
('drfad', 1989, ["dr. fad", "dr fad show"], None),
('funhouse', 1989, ["fun house", "funhouse"], r"j\.? ?d\.? roth|game ?show|fox fun house|college mad house|\b(1988|1989|199[01])\b"),
('imtelling', 1987, ["i'm telling!", "i'm telling", "im telling"], r"game ?show|nbc|1987|1988|laurie faso"),
('wideworldkids', 1993, ["wide world of kids"], None),
('notjustnews', 1993, ["not just news", "real news for kids"], None),
('garfieldfriends', 1990, ["garfield and friends", "garfield & friends"], None),
('garfieldspecial', 1986, ["garfield's halloween", "garfield christmas", "garfield's thanksgiving", "garfield in the rough", "garfield on the town", "here comes garfield", "garfield in paradise", "garfield goes hollywood", "garfield: his 9 lives", "garfield's babes and bullets", "garfield's feline fantasies", "garfield gets a life", "garfield tv special", "garfield special"], None),
('alvin', 1986, ["alvin and the chipmunks", "alvin & the chipmunks", "the chipmunks go to the movies"], r"198\d|199[0-9]|episode|season|s0?\d|nbc|cartoon|series|vhs|christmas|halloween|adventure"),
('heathcliff', 1985, ["heathcliff"], r"catillac|cartoon|episode|season|s0?\d|\b198[0-8]\b|series|vhs|dic"),
('gadget', 1985, ["inspector gadget"], r"198[3-9]|199\d|episode|season|s0?\d|cartoon|series|vhs|saves christmas|dic"),
('dennis', 1987, ["dennis the menace"], r"198[6-8]|animated|cartoon|dic|episode|s0?\d"),
('filmationgb', 1986, ["filmation's ghostbusters", "filmation ghostbusters"], None),
('realgb', 1988, ["the real ghostbusters", "real ghostbusters", "slimer! and the real ghostbusters"], None),
('beetlejuice', 1990, ["beetlejuice"], r"animated|cartoon|episode|season|s0?\d|series|abc|fox kids"),
('bobbysworld', 1992, ["bobby's world", "bobbys world"], None),
('eek', 1993, ["eek! the cat", "eek the cat", "eek!stravaganza", "eekstravaganza"], None),
('tinytoon', 1991, ["tiny toon adventures", "tiny toons"], None),
('animaniacs', 1994, ["animaniacs"], r"^(?!.*\b20(1\d|2\d)\b)"),
('tazmania', 1992, ["taz-mania", "tazmania"], r"episode|season|s0?\d|cartoon|series|fox|\b199[1-5]\b"),
('waldo', 1991, ["where's waldo"], r"episode|animated|cartoon|series|cbs|1991|s0?\d"),
('madeline', 1994, ["madeline"], r"animated|cartoon|episode|special|s0?\d|new adventures|madeline's|madeline and|madeline in|madeline at|vhs"),
('recess', 1998, ["disney's recess", "recess"], r"disney|episode|season|s0?\d|t\.?j\.?|one saturday morning|school's out|taking the fifth|miracle on third"),
('pepperann', 1998, ["pepper ann"], None),
('doug', 1993, ["doug"], r"^(disney'?s? |brand spanking new!? |nickelodeon'?s? )?doug\b.*(nick|disney|season|episode|s0?\d|funnie|vhs|christmas|halloween|\b199\d\b)|doug'?s (1st|first) movie|doug funnie"),
('weekenders', 2000, ["the weekenders"], None),
('kimpossible', 2003, ["kim possible"], r"200[234]|season [12]\b|s0[12]|so the drama|sitch in time"),
('lilostitch', 2003, ["lilo & stitch: the series", "lilo and stitch the series", "lilo & stitch the series"], None),
('proudfamily', 2002, ["the proud family", "proud family"], r"^(?!.*louder)"),
('fillmore', 2003, ["fillmore!"], r"disney|episode|season|s0?\d|abc"),
('houseofmouse', 2001, ["house of mouse"], None),
('hercules', 1998, ["hercules: the animated series", "hercules the animated series", "disney's hercules", "hercules the series", "hercules animated series", "hercules tv series"], r"series|episode|s0?\d"),
('timonpumbaa', 1996, ["timon & pumbaa", "timon and pumbaa"], None),
('aladdin', 1995, ["aladdin: the series", "aladdin the series", "aladdin tv series", "aladdin animated series"], None),
('mermaid', 1993, ["the little mermaid: the series", "little mermaid tv series", "little mermaid the series", "little mermaid animated series"], None),
('bonkers', 1994, ["bonkers"], r"disney|bobcat|episode|season|s0?\d|cartoon|series|toon"),
('quackpack', 1996, ["quack pack"], None),
('dalmatians', 1998, ["101 dalmatians: the series", "101 dalmatians the series"], None),
('junglecubs', 1997, ["jungle cubs"], None),
('mightyducks', 1996, ["mighty ducks: the animated series", "mighty ducks the animated series", "mighty ducks animated"], None),
('schoolhouse', 1990, ["schoolhouse rock", "school house rock"], r"^(?!.*(live|musical|cover|karaoke|band))"),
('histeria', 1999, ["histeria!"], r"episode|season|s0?\d|wb|cartoon|series"),
('heyarnold', 1998, ["hey arnold"], None),
('thornberrys', 1999, ["wild thornberrys"], None),
('ginger', 2001, ["as told by ginger"], None),
('rocketpower', 2000, ["rocket power"], r"nick|episode|season|s0?\d|otto|cartoon|series|vhs|race across"),
('chalkzone', 2002, ["chalkzone", "chalk zone"], None),
('teenagerobot', 2003, ["my life as a teenage robot"], None),
('cartooncartoon', 1999, ["cartoon cartoon fridays", "cartoon cartoon show", "cartoon cartoons", "what a cartoon"], None),
('ededdeddy', 2000, ["ed, edd n eddy", "ed edd n eddy", "ed, edd 'n eddy"], None),
('knd', 2003, ["codename: kids next door", "codename kids next door", "kids next door"], None),
('dexter', 1998, ["dexter's laboratory", "dexters laboratory", "dexter's lab"], None),
('powerpuff', 1999, ["powerpuff girls"], r"^(?!.*\b(2016|2017|2018|2019|reboot|z\b))"),
('courage', 2000, ["courage the cowardly dog"], None),
('johnnybravo', 1998, ["johnny bravo"], None),
('scooby', 1989, ["a pup named scooby-doo", "pup named scooby doo", "what's new, scooby-doo", "what's new scooby-doo", "whats new scooby doo", "13 ghosts of scooby-doo", "13 ghosts of scooby doo", "new scooby-doo mysteries", "scooby-doo, where are you", "scooby doo where are you", "scooby-doo show", "scooby-doo and scrappy-doo", "scooby doo and scrappy doo", "new scooby-doo movies", "new scooby doo movies", "scooby-doo meets the boo brothers", "scooby-doo and the ghoul school", "scooby-doo and the reluctant werewolf", "scooby-doo on zombie island", "scooby-doo and the witch's ghost", "scooby-doo and the alien invaders", "scooby-doo and the cyber chase"], None),
('flintstonekids', 1987, ["flintstone kids"], None),
('tomjerrykids', 1991, ["tom & jerry kids", "tom and jerry kids"], None),
('yoyogi', 1991, ["yo yogi"], None),
('smurfs', 1986, ["the smurfs", "smurfs"], r"198\d|episode|season|s0?\d|cartoon|hanna|nbc|series|vhs|christmas|special|adventures"),
('snorks', 1986, ["snorks"], None),
('jetsons', 1986, ["the jetsons"], r"198[5-9]|1990|episode|season|s0?\d|cartoon|series|meet the flintstones|rockin|movie"),
('popeyeson', 1987, ["popeye and son"], None),
('fatalbert', 1985, ["fat albert"], r"cosby kids|episode|season|s0?\d|cartoon|series|special|christmas|halloween|easter"),
('peanuts', 1988, ["charlie brown", "snoopy", "peanuts"], r"charlie brown (christmas|thanksgiving|valentine|all-stars|all stars)|great pumpkin|easter beagle|charlie brown and snoopy show|this is america,? charlie brown|you're (a good|in love|not elected|the greatest|a good sport|in the super bowl)|it's (the|a|an|your|flashbeagle|magic|arbor|spring|christmastime|the girl|the pied) .*charlie brown|snoopy'?s? (getting married|reunion|come home)|snoopy!+ the musical|happy new year,? charlie brown|race for your life|bon voyage|boy named charlie brown|peanuts.*(special|cbs|specials)|he's (your dog|a bully)|she's a good skate|what a nightmare|why,? charlie brown|is this goodbye|someday you'll find her|life is a circus|what have we learned|there's no time for love|play it again|you don't look 40|i want a dog for christmas|lucy must be traded|charlie brown's christmas tales|be my valentine|you're a good man"),
('seuss', 1988, ["dr. seuss", "dr seuss"], r"grinch|cat in the hat|lorax|horton|sneetches|butter battle|pontoffel|hoober|halloween is grinch|daisy-head|on the loose|wubbulous|special|animated|cbs|vhs|video"),
('rankinbass', 1988, ["rankin/bass", "rankin bass", "rudolph the red-nosed reindeer", "frosty the snowman", "santa claus is comin' to town", "year without a santa claus", "little drummer boy", "here comes peter cottontail", "rudolph's shiny new year", "jack frost", "nestor the long-eared", "twas the night before christmas", "'twas the night before christmas", "frosty's winter wonderland", "rudolph and frosty", "first christmas snow", "pinocchio's christmas", "leprechaun's christmas gold", "life and adventures of santa claus", "mad monster party", "the hobbit 1977", "return of the king 1980", "flight of dragons", "easter bunny is comin' to town", "first easter rabbit", "stingiest man in town", "cricket on the hearth", "frosty returns"], r"^(?!.*(soundtrack|album|song|cover|reaction|review))"),
('kidholiday', 1990, ["halloween special", "christmas special", "thanksgiving special", "easter special", "valentine special", "valentine's day special", "holiday special"], r"(cartoon|animated|kids|children|muppet|disney|nickelodeon|nick|garfield|charlie brown|smurf|chipmunk|care bears|claymation|will vinton|raisins|bugs bunny|looney|flintstone|yogi|scooby|pac-man|strawberry|rainbow brite|he-man|she-ra|inspector gadget|ziggy|cathy|family circus|berenstain|for better or for worse|b\.?c\.?|wizard of id|pound puppies|pee-?wee|sesame|barney|tiny toon|animaniacs|rugrats|doug|simpsons|casper|frosty|rudolph|grinch|winnie|pooh|mickey|donald|goofy|peanuts|snoopy|raggedy|teddy ruxpin|fraggle|alf|punky|chucklewood|buttons|rusty|bill melendez|nelvana|rankin|hanna|dic|filmation)"),
('wwod', 1989, ["wonderful world of disney", "disney sunday movie", "magical world of disney", "disney's wonderful world", "walt disney's wonderful world of color", "disney night at the movies", "abc disney movie"], None),
('kidsvariety', 1990, ["kids' wb", "kids wb", "fox kids", "one saturday morning", "saturday morning cartoons", "abc saturday morning", "cbs saturday morning", "nbc saturday morning", "disney afternoon"], r"(\b(198[4-9]|199\d|200[0-4])\b)"),
('muppets', 1990, ["muppet babies", "the muppet show", "muppets tonight", "jim henson hour", "fraggle rock", "the storyteller", "dinosaurs 1991", "mother goose stories", "dog city", "muppet family christmas", "muppets celebration", "jim henson's"], r"^(?!.*(2015|2020|2021|2022|back to the rock|mayhem|now\b))"),
('stories', 1990, ["faerie tale theatre", "shelley duvall", "tall tales & legends", "tall tales and legends", "shelley duvall's bedtime stories", "storybook classics", "rabbit ears", "we all have tales", "american heroes & legends", "hbo storybook musicals", "happily ever after: fairy tales", "happily ever after fairy tales", "long ago and far away", "grimm's fairy tale classics", "grimm masterpiece theatre", "saban's adventures", "my favorite fairy tales", "britannica's tales around the world", "the little prince 1982", "adventures of the little koala", "noozles", "maya the bee", "david the gnome", "the world of david the gnome", "mysterious cities of gold", "belle and sebastian", "the littl' bits", "little bits", "spartakus and the sun beneath the sea", "maple town", "sylvanian families", "ox tales", "grimm's fairy tales"], None),
('nickcartoon', 1989, ["nickelodeon livewire", "nickelodeon out of control", "out of control dave coulier", "nickelodeon total panic", "nickelodeon pinwheel", "pinwheel nickelodeon", "kablam!", "nickelodeon special delivery", "nickelodeon the third eye", "nickelodeon rated k", "nicktoons 1991", "nicktoons tv", "count duckula", "danger mouse", "looney tunes on nickelodeon", "nickelodeon looney tunes", "today's special", "the elephant show", "sharon, lois & bram", "sharon lois and bram", "fred penner", "eureeka's castle", "the adventures of the little prince", "the tomfoolery show", "turkey television", "standby... lights! camera! action!", "kids' court", "kids court", "don't just sit there", "nick rocks", "sk8 tv", "sk8-tv", "dusty's treehouse", "bananaz", "kid's writes", "kids writes", "nickel flicks", "america goes bananaz", "what will they think of next", "first row features", "nick's thanksgiving fest", "u-pick live", "slime time live", "action league now", "oh yeah! cartoons", "oh yeah cartoons", "the adventures of jimmy neutron", "invader zim", "the fairly oddparents", "fairly odd parents"], r"^(?!.*\b20(0[5-9]|1\d|2\d)\b)"),
('extra', 1992, ["captain kangaroo", "the electric company", "zoobilee zoo", "kidsongs", "wee sing", "the big comfy couch", "big comfy couch", "shining time station", "lamb chop's play-along", "lamb chop's play along", "the puzzle place", "puzzle place", "tots tv", "storytime pbs", "imagination station", "romper room", "the great space coaster", "great space coaster", "hot fudge show", "kids like you", "the letter people", "pappyland", "the reppies", "the huggabug club", "gerbert", "the adventures of dudley the dragon", "dudley the dragon", "groundling marsh", "the noddy shop", "noddy shop", "wimzie's house", "wimzies house", "the charlie horse music pizza", "charlie horse music pizza", "in the mix pbs", "kino's storytime", "bookmice", "owl/tv", "owl tv", "popular mechanics for kids", "the new ghostwriter mysteries", "science court", "squigglevision", "mad scientist toon club", "what's up doc", "really wild animals", "national geographic kids video", "kratt brothers: be the creature", "wild america", "mutual of omaha's spirit of adventure", "the secret city", "pappyland", "bill cosby's picture pages", "picture pages", "mr. dressup", "mr dressup", "the friendly giant", "polka dot door", "under the umbrella tree", "fred penner's place", "the elephant show", "mcgee and me", "adventures in odyssey", "the adventures of the galaxy rangers", "hey vern, it's ernest", "hey vern it's ernest", "wonder showzen", "small wonder", "out of this world", "my secret identity", "the new leave it to beaver", "punky brewster", "the wonder years", "mr. belvedere", "harry and the hendersons", "superboy", "the adventures of sinbad", "the new lassie", "lassie 1997", "the new adventures of flipper", "flipper 1995", "big bad beetleborgs", "mystic knights of tir na nog", "tattooed teenage alien fighters", "superhuman samurai syber-squad", "vr troopers", "masked rider", "ninja turtles: the next mutation", "power rangers", "sweet valley high", "breaker high", "student bodies", "radio active", "the tribe", "ocean girl", "spellbinder", "round the twist", "the adventures of swiss family robinson", "my babysitter's a vampire", "honey, i shrunk the kids: the tv show", "honey i shrunk the kids tv", "the torkelsons", "smart guy", "the jersey", "in a heartbeat", "the famous jett jackson", "bug juice", "totally circus", "totally hoops", "going wild with jeff corwin", "omba mokomba", "off the wall disney", "mad libs disney", "z games", "pb&j otter", "teen win lose or draw", "win lose or draw teen", "mickey mouse club 1977", "new mickey mouse club", "you and me kid", "disney's contraption", "contraption disney", "wind in the willows", "welcome to pooh corner", "the edison twins", "edison twins", "five mile creek", "still the beaver", "the campbells", "road to avonlea", "avonlea", "anne of green gables 1985", "ready or not 1993", "my life as a dog tv", "the zack files", "zack files", "i was a sixth grade alien", "mentors tv", "the odyssey 1992", "northwood", "fifteen nickelodeon", "fifteen 1991", "hillside nickelodeon", "the secret world of og", "scholastic's the magic school bus", "reading rainbow", "the puzzle place", "where's waldo", "mister rogers", "mr. rogers' neighborhood"], r"^(?!.*\b(20(0[5-9]|1\d|2\d))\b)"),
('disneytoon', 1990, ["disney dtv", "dtv valentine", "dtv monster hits", "dtv doggone valentine", "disney's gargoyles", "gargoyles season", "gargoyles episode", "gargoyles the heroes awaken", "gargoyles: the goliath chronicles", "disney's marsupilami", "teacher's pet disney", "disney's teacher's pet", "the mouse factory", "ducktales", "chip 'n dale rescue rangers", "chip n dale rescue rangers", "talespin", "darkwing duck", "goof troop", "adventures of the gummi bears", "gummi bears", "the wuzzles", "new adventures of winnie the pooh", "welcome to pooh corner", "dumbo's circus", "donald duck presents", "good morning, mickey", "mickey's mouse tracks", "mickey mouse works", "disney's sing along songs", "disney sing-along songs", "buzz lightyear of star command", "the legend of tarzan", "teamo supremo", "lloyd in space", "sabrina the animated series", "sabrina: the animated series", "the new adventures of madeline", "nightmare ned", "the shnookums and meat", "raw toonage"], r"^(?!.*\b(2017|2018|2019|202\d|reboot)\b)"),
('othertoon', 1990, ["franklin the turtle", "franklin and friends", "babar the elephant", "babar tv series", "babar animated", "star wars: droids", "star wars droids", "star wars: ewoks", "star wars ewoks", "rupert bear", "rupert animated", "caillou season", "caillou episode", "caillou vhs", "the tick animated", "the tick 1994", "cubix: robots for everyone", "sagwa, the chinese siamese cat", "sagwa the chinese siamese cat", "maurice sendak's little bear", "little bear nick jr", "the littles cartoon", "the littles 1983", "popples cartoon", "popples 1986", "wish kid starring macaulay culkin", "prostars cartoon", "hammerman cartoon", "muppet babies", "care bears", "rainbow brite", "strawberry shortcake", "my little pony", "pound puppies", "the get along gang", "get along gang", "kissyfur", "the wuzzles", "foofur", "the snorks", "paw paws", "pac-man cartoon", "pac-man animated", "rubik the amazing cube", "the gary coleman show", "pole position", "mister t cartoon", "hulk hogan's rock 'n' wrestling", "rock 'n' wrestling", "the 13 ghosts", "galaxy high", "teen wolf cartoon", "teen wolf animated", "alf: the animated series", "alf tales", "the berenstain bears", "berenstain bears", "the raccoons", "the adventures of tintin", "the busy world of richard scarry", "richard scarry", "the magic school bus", "the adventures of teddy ruxpin", "teddy ruxpin", "lady lovely locks", "moondreamers", "glo friends", "potato head kids", "my pet monster", "beverly hills teens", "maxie's world", "it's punky brewster", "punky brewster cartoon", "the new archies", "camp candy", "captain n", "super mario bros. super show", "super mario bros super show", "adventures of super mario bros. 3", "super mario world cartoon", "the legend of zelda cartoon", "sonic the hedgehog", "adventures of sonic the hedgehog", "kid 'n play", "new kids on the block cartoon", "back to the future: the animated series", "back to the future animated", "the addams family 1992", "fievel's american tails", "the little rascals cartoon", "problem child cartoon", "attack of the killer tomatoes cartoon", "beethoven animated", "free willy animated", "ace ventura: pet detective animated", "the mask: animated series", "the mask animated", "dumb and dumber animated", "jumanji animated", "jumanji: the animated series", "men in black: the series", "the magic school bus", "c bear and jamal", "life with louie", "bump in the night", "the twisted tales of felix the cat", "what-a-mess", "santo bugito", "the adventures of hyperman", "earthworm jim", "freakazoid", "pinky and the brain", "pinky, elmyra", "the sylvester & tweety mysteries", "sylvester and tweety mysteries", "road rovers", "the zeta project", "static shock", "ozzy & drix", "ozzy and drix", "mucha lucha", "xiaolin showdown", "what's new scooby", "jackie chan adventures", "the mummy: the animated series", "generation o", "rescue heroes", "dragon tales", "clifford the big red dog", "george shrinks", "seven little monsters", "the berenstain bears 2003", "angelina ballerina", "maya & miguel", "postcards from buster"], r"^(?!.*\b(20(0[5-9]|1\d|2\d))\b)"),
]
JUNK = re.compile(r"\b(grounded|goanimate|vyond|death battle|lecture|sermon|church|meeting|council|commission|selectmen|school board|board of|county|city of|public library|newsreel|inauguration|football|hockey|basketball|baseball|soccer|ruined|iceberg|video essay|analysis|facts about|the (rise|fall) of|history of|tvrip|laserdisc|periscope|trailers?|teasers?|review(s|ed)?|reaction|react|retrospective|ranking|ranked|top \d+|podcast|commentary|fan ?made|fan ?edit|fandub|fan dub|parody|ytp|amv|abridged|remix|mashup|tribute|theme song|soundtrack|ost|album|karaoke|cover|lyrics|gameplay|walkthrough|longplay|playthrough|let'?s play|speedrun|rom|iso\b|nes\b|snes\b|genesis\b|game boy|gba\b|ps1\b|ps2\b|playstation|xbox|pc game|cd-rom|commodore|amiga|atari|dos game|video game|storybook app|read aloud|read-aloud|audiobook|audio book|book scan|comic|comics|coloring|magazine|script|toy|toys|unboxing|commercial compilation|bumpers? compilation|promos? compilation|interview|panel|q&a|convention|lost media|creepypasta|theory|explained|documentary about|behind the scenes|bloopers|outtakes|opening and closing|opening to|closing to|intro only|credits only)\b", re.I)
CODES = re.compile(r"\b(FR|VF|VOSTFR|PL|ITA|ESP|GER|NL|JP|JPN|BR|PT-BR|LAT|RUS|SWE|NOR|DAN|FIN)\b")
FOREIGN = re.compile(r"(castellano|espa[nñ]ol|latino|doblaje|dublado|portugu[eê]s|brasil|deutsch|german dub|fran[cç]ais|french dub|vf\b|italiano|ita\b|nederlands|dutch dub|svenska|norsk|dansk|suomi|polski|polish|lektor|dubbing pl|magyar|hungarian|rom[aâ]n[aă]|czech|[čc]esky|русск|russian|ukrain|greek|ελλην|turkish|t[uü]rk[cç]e|arabic|hebrew|עברית|hindi|tamil|telugu|urdu|bengali|indonesia|malay|tagalog|filipino|thai|viet|korean|한국|japanese dub|日本|中文|國語|粤語|cantonese|mandarin|[Ѐ-ӿ֐-ۿ぀-ヿ一-鿿가-힯])", re.I)
MODERN = re.compile(r"(?<!\d)(20(0[5-9]|1\d|2\d))(?!\d)")
ERA = re.compile(r"(?<!\d)(198[4-9]|199\d|200[0-4])(?!\d)")
OLD = re.compile(r"(?<!\d)(19[0-7]\d|198[0-3])(?!\d)")
def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if k == tries - 1:
                print('fail', url[:110], e, flush=True); return None
            time.sleep(3 * (k + 1))
def scrape(q):
    out, cursor = [], None
    while True:
        u = 'https://archive.org/services/search/v1/scrape?' + urllib.parse.urlencode({'fields': 'identifier,title,date,year,downloads,language,subject', 'q': q, 'count': 5000, **({'cursor': cursor} if cursor else {})})
        j = get(u)
        if not j: break
        out += j.get('items', [])
        cursor = j.get('cursor')
        if not cursor or len(out) > 40000: break
    return out
def norm(s):
    return re.sub(r"\s+", ' ', re.sub(r"[’`]", "'", str(s or '').lower())).strip()
def search(sh):
    tag, yr, phrases, rx = sh
    ph = ' OR '.join('"' + p.replace('"', '') + '"' for p in phrases)
    items = scrape('mediatype:movies AND (title:(' + ph + ') OR subject:(' + ph + '))')
    keep = []
    crx = re.compile(rx, re.I) if rx else None
    for it in items:
        t = it.get('title')
        if isinstance(t, list): t = ' '.join(t)
        low = norm(t)
        if not low or it['identifier'] in have: continue
        if not any(norm(p) in low for p in phrases) and not (crx is None and any(norm(p) in norm(it.get('subject') if not isinstance(it.get('subject'), list) else ';'.join(it.get('subject'))) for p in phrases) and re.search(r'episode|season|s0?\d+ ?e\d+|\bvhs\b', low)): continue
        if JUNK.search(low) or FOREIGN.search(low) or CODES.search(str(t)) or low.endswith('?'): continue
        if re.search(r'\b\d{1,2}[/.-]\d{1,2}[/.-](0[5-9]|1\d|2\d)\b', low): continue
        sj = it.get('subject')
        if isinstance(sj, list): sj = ';'.join(sj)
        ctx = low + ' ; ' + norm(sj)
        lang = it.get('language')
        if isinstance(lang, list): lang = ' '.join(lang)
        if lang and not re.search(r'eng|english|^en\b', str(lang).lower()): continue
        if MODERN.search(low) and not ERA.search(low): continue
        if crx and not (crx.search(low) if crx.pattern.startswith('^') else crx.search(ctx)): continue
        it['title'] = t; it['k'] = tag; it['yr'] = yr
        keep.append(it)
    return tag, len(items), keep
seen = {}
found = collections.Counter(); rawhits = {}
with ThreadPoolExecutor(8) as ex:
    for tag, n, keep in ex.map(search, S):
        rawhits[tag] = n
        for it in keep:
            if it['identifier'] not in seen:
                seen[it['identifier']] = it; found[tag] += 1
        print('search', tag, n, len(keep), 'total', len(seen), flush=True)
R2 = [
("Rugrats", 1991, 2004), ("Rocko's Modern Life", 1993, 1996), ("The Ren & Stimpy Show", 1991, 1996), ("The Angry Beavers", 1997, 2001), ("CatDog", 1998, 2004), ("SpongeBob SquarePants", 1999, 2004), ("Aaahh!!! Real Monsters", 1994, 1997), ("The Fairly OddParents", 2001, 2004), ("The Adventures of Jimmy Neutron", 2002, 2004), ("Invader Zim", 2001, 2003), ("Hey Arnold!", 1996, 2004), ("Doug", 1991, 1999), ("The Wild Thornberrys", 1998, 2004), ("Rocket Power", 1999, 2004), ("KaBlam!", 1996, 2000), ("Clarissa Explains It All", 1991, 1994), ("Salute Your Shorts", 1991, 1992), ("Hey Dude", 1989, 1991), ("The Secret World of Alex Mack", 1994, 1998), ("Kenan & Kel", 1996, 2000), ("The Adventures of Pete & Pete", 1993, 1996), ("Legends of the Hidden Temple", 1993, 1995), ("Nickelodeon GUTS", 1992, 1995), ("Nick Arcade", 1992, 1993), ("Wild & Crazy Kids", 1990, 1992), ("What Would You Do?", 1991, 1993), ("Welcome Freshmen", 1991, 1993), ("The Mystery Files of Shelby Woo", 1996, 1998), ("Space Cases", 1996, 1997), ("Fifteen", 1991, 1993), ("Inspector Gadget", 1984, 1986), ("Danger Mouse", 1984, 1992), ("Count Duckula", 1988, 1993), ("David the Gnome", 1987, 1988), ("Looney Tunes on Nickelodeon", 1988, 1999),
("DuckTales", 1987, 1990), ("Chip 'n Dale Rescue Rangers", 1989, 1990), ("TaleSpin", 1990, 1991), ("Darkwing Duck", 1991, 1992), ("Goof Troop", 1992, 1993), ("Bonkers", 1993, 1994), ("Gargoyles", 1994, 1997), ("Adventures of the Gummi Bears", 1985, 1991), ("The Wuzzles", 1985, 1985), ("Aladdin", 1994, 1995), ("The Little Mermaid", 1992, 1994), ("Timon & Pumbaa", 1995, 1999), ("Quack Pack", 1996, 1996), ("Mighty Ducks", 1996, 1997), ("Jungle Cubs", 1996, 1998), ("101 Dalmatians: The Series", 1997, 1998), ("Hercules", 1998, 1999), ("Recess", 1997, 2001), ("Pepper Ann", 1997, 2000), ("Teacher's Pet", 2000, 2002), ("The Weekenders", 2000, 2004), ("Lloyd in Space", 2001, 2004), ("Buzz Lightyear of Star Command", 2000, 2001), ("The Legend of Tarzan", 2001, 2003), ("Kim Possible", 2002, 2004), ("The Proud Family", 2001, 2004), ("Lilo & Stitch: The Series", 2003, 2004), ("Even Stevens", 2000, 2003), ("Lizzie McGuire", 2001, 2004), ("That's So Raven", 2003, 2004), ("The Famous Jett Jackson", 1998, 2001), ("So Weird", 1999, 2001), ("Bug Juice", 1998, 2001), ("Kids Incorporated", 1984, 1993), ("Welcome to Pooh Corner", 1984, 1986),
("Mighty Morphin Power Rangers", 1993, 1996), ("Power Rangers", 1993, 2004), ("VR Troopers", 1994, 1996), ("Masked Rider", 1995, 1996), ("Big Bad Beetleborgs", 1996, 1998), ("Bobby's World", 1990, 1998), ("Eek! The Cat", 1992, 1997), ("Life with Louie", 1995, 1998), ("The Tick", 1994, 1996), ("Goosebumps", 1995, 1998), ("Where on Earth Is Carmen Sandiego?", 1994, 1999), ("The Magic School Bus", 1994, 1997), ("Attack of the Killer Tomatoes", 1990, 1991), ("Peter Pan and the Pirates", 1990, 1991), ("Taz-Mania", 1991, 1995), ("Tiny Toon Adventures", 1990, 1995), ("Animaniacs", 1993, 1998), ("Pinky and the Brain", 1995, 1998), ("Freakazoid!", 1995, 1997), ("The Sylvester & Tweety Mysteries", 1995, 2000), ("Histeria!", 1998, 2000), ("Road Rovers", 1996, 1997), ("Earthworm Jim", 1995, 1996), ("Men in Black: The Series", 1997, 2001), ("Jackie Chan Adventures", 2000, 2004), ("Static Shock", 2000, 2004), ("Sabrina: The Animated Series", 1999, 2000), ("Mummies Alive!", 1997, 1997), ("Big Guy and Rusty the Boy Robot", 1999, 2001), ("Yu-Gi-Oh!", 2001, 2004), ("Cardcaptors", 2000, 2001), ("Digimon", 1999, 2003), ("Monster Rancher", 1999, 2001), ("Medabots", 2001, 2004), ("Beyblade", 2002, 2004), ("Zoids", 2001, 2004),
("Dexter's Laboratory", 1996, 2003), ("Johnny Bravo", 1997, 2004), ("Cow and Chicken", 1997, 1999), ("I Am Weasel", 1997, 2000), ("The Powerpuff Girls", 1998, 2004), ("Ed, Edd n Eddy", 1999, 2004), ("Courage the Cowardly Dog", 1999, 2002), ("Mike, Lu & Og", 1999, 2001), ("Sheep in the Big City", 2000, 2002), ("Time Squad", 2001, 2003), ("Samurai Jack", 2001, 2004), ("Grim & Evil", 2001, 2004), ("Codename: Kids Next Door", 2002, 2004), ("Whatever Happened to Robot Jones?", 2002, 2003), ("What a Cartoon!", 1995, 1997), ("2 Stupid Dogs", 1993, 1995), ("SWAT Kats", 1993, 1995), ("The Pirates of Dark Water", 1991, 1993), ("Captain Planet and the Planeteers", 1990, 1996), ("The Real Adventures of Jonny Quest", 1996, 1997), ("Space Ghost Coast to Coast", 1994, 2004), ("Cartoon Planet", 1995, 1998), ("Toonami", 1997, 2004), ("Cartoon Network", 1992, 2004),
("The Real Ghostbusters", 1986, 1991), ("Alvin and the Chipmunks", 1984, 1990), ("Muppet Babies", 1984, 1991), ("Garfield and Friends", 1988, 1994), ("Pee-wee's Playhouse", 1986, 1990), ("Beetlejuice", 1989, 1991), ("The Smurfs", 1984, 1989), ("The Snorks", 1984, 1989), ("Dungeons & Dragons", 1984, 1985), ("Pole Position", 1984, 1984), ("Kidd Video", 1984, 1985), ("The Littles", 1984, 1985), ("Heathcliff", 1984, 1988), ("Punky Brewster", 1985, 1986), ("Hulk Hogan's Rock 'n' Wrestling", 1985, 1986), ("The 13 Ghosts of Scooby-Doo", 1985, 1985), ("A Pup Named Scooby-Doo", 1988, 1991), ("The Flintstone Kids", 1986, 1988), ("Foofur", 1986, 1988), ("Galaxy High", 1986, 1986), ("Teen Wolf", 1986, 1987), ("ALF: The Animated Series", 1987, 1989), ("Dennis the Menace", 1986, 1988), ("The Super Mario Bros. Super Show!", 1989, 1989), ("The Adventures of Super Mario Bros. 3", 1990, 1990), ("Super Mario World", 1991, 1991), ("Captain N: The Game Master", 1989, 1991), ("The Legend of Zelda", 1989, 1989), ("Adventures of Sonic the Hedgehog", 1993, 1993), ("Sonic the Hedgehog", 1993, 1994), ("Back to the Future", 1991, 1992), ("Bill & Ted's Excellent Adventures", 1990, 1991), ("Camp Candy", 1989, 1992), ("Saved by the Bell", 1989, 1993), ("California Dreams", 1992, 1996), ("Hang Time", 1995, 2000), ("City Guys", 1997, 2001), ("One Saturday Morning", 1997, 2002), ("ReBoot", 1994, 2001), ("Bump in the Night", 1994, 1995), ("Free Willy", 1994, 1995), ("The Bugs Bunny & Tweety Show", 1986, 2000), ("Schoolhouse Rock!", 1984, 2001), ("Fat Albert and the Cosby Kids", 1984, 1985), ("CBS Storybreak", 1985, 1998), ("ABC Weekend Special", 1984, 1997), ("Beakman's World", 1992, 1998), ("Bill Nye the Science Guy", 1993, 1998), ("Science Court", 1997, 2000), ("Disney's Doug", 1996, 1999), ("Fox Kids", 1990, 2002), ("Kids' WB", 1995, 2004), ("Saturday morning cartoons", 1984, 2004),
("Square One TV", 1987, 1994), ("3-2-1 Contact", 1984, 1988), ("Ghostwriter", 1992, 1995), ("Where in the World Is Carmen Sandiego?", 1991, 1995), ("Where in Time Is Carmen Sandiego?", 1996, 1997), ("Wishbone", 1995, 1998), ("Kratts' Creatures", 1996, 1996), ("Zoom", 1999, 2004), ("Reading Rainbow", 1984, 2004), ("Mister Rogers' Neighborhood", 1984, 2001), ("Shining Time Station", 1989, 1995), ("Lamb Chop's Play-Along", 1992, 1995), ("The Puzzle Place", 1995, 1998), ("Storytime", 1992, 1998), ("Newton's Apple", 1984, 1998), ("The Big Comfy Couch", 1995, 2004), ("Captain Kangaroo", 1984, 1993), ("Romper Room", 1984, 1994), ("Zoobilee Zoo", 1986, 1987), ("Eureeka's Castle", 1989, 1995), ("Gullah Gullah Island", 1994, 1998), ("Today's Special", 1984, 1987), ("Sharon, Lois & Bram's Elephant Show", 1984, 1989), ("Wee Sing", 1985, 1996), ("Theodore Tugboat", 1996, 2001), ("Wimzie's House", 1997, 2001), ("Sagwa, the Chinese Siamese Cat", 2001, 2004), ("Tots TV", 1996, 1998), ("The Get Along Gang", 1984, 1986), ("Dumbo's Circus", 1985, 1986), ("Mousercise", 1984, 1996), ("The Busy World of Richard Scarry", 1994, 1997), ("The Adventures of Teddy Ruxpin", 1987, 1987), ("Pound Puppies", 1986, 1989), ("Rainbow Brite", 1984, 1986), ("Jem", 1985, 1988), ("She-Ra: Princess of Power", 1985, 1987), ("Care Bears", 1985, 1988), ("My Little Pony 'n Friends", 1986, 1987), ("Popples", 1986, 1987), ("The Raccoons", 1985, 1992), ("Babar", 1989, 1991), ("The Adventures of Tintin", 1991, 1992), ("Little Lulu", 1995, 1999), ("Madeline", 1989, 2001), ("Anne of Green Gables: The Animated Series", 2001, 2002), ("The Baby-Sitters Club", 1990, 1990), ("Ramona", 1988, 1989), ("Are You Afraid of the Dark?", 1991, 2000), ("Animorphs", 1998, 1999), ("Eerie, Indiana", 1991, 1992), ("The Torkelsons", 1991, 1992), ("Out of the Box", 1998, 2004),
]

LUMP = {'extra', 'othertoon', 'disneytoon', 'nickcartoon', 'kidsvariety', 'nickblock', 'disneychan', 'cartooncartoon', 'snick', 'muppets', 'stories'}
def sq(x): return re.sub(r'[^a-z0-9]+', ' ', norm(x).replace('&', ' and ')).strip()
DISC = re.compile(r"\b(s\d{1,2} ?e\d{1,3}|s\d{1,2}|season \d|seasons? |series \d|episodes?\b|ep \d|eps\b|vol(ume)? ?\d|complete|the series|animated series|tv series|cartoon|tv ?rip|with commercials|w commercials|woc|nickelodeon|nicktoons?|nick jr|disney channel|toon disney|disney afternoon|fox kids|kids wb|cartoon network|toonami|pbs|abc|cbs|nbc|upn|syndicated|saturday morning|\d{1,2}x\d{2}|part \d|disc \d|full episodes?|pilot|marathon|block|aired|broadcast)\b")
AMB2 = {'Hang Time', 'City Guys', 'Space Cases', 'Free Willy', 'Teen Wolf', 'Bug Juice', 'Time Squad', 'Road Rovers', 'Back to the Future', 'The Little Mermaid', 'Mighty Ducks', 'Care Bears', 'Pole Position', 'Galaxy High', 'Camp Candy', 'Science Court', 'Out of the Box', 'Super Mario World', 'The Legend of Zelda', 'Sonic the Hedgehog', 'Dennis the Menace', 'Dungeons & Dragons', 'The Tick', 'Cartoon Network', 'The Legend of Tarzan', 'Pound Puppies', 'Rainbow Brite', 'Power Rangers', 'Wee Sing', 'Fat Albert and the Cosby Kids'}
STOPW = {'the', 'a', 'an', 'of', 'and', 'in', 'on', 'is', 'to', 'n', 's', 'show', 'series', 'adventures', 'new'}
J2 = re.compile(r"\b(longplay|replay|game grumps|nostalgia critic|critic|review|reviews|livestream|deathstream|stream|happy meal|reaction|reacts?|podcast|minecraft|roblox|ptbr|pt br|episodio|annotated|storyboard|recreation|recreated|recreat|self insert|rewind|commentary|ranking|ranked|top \d+|explained|interview|trailer|teaser|promos?|bumpers?|tabletop|actual play|campaign|rpg|speedrun|walkthrough|gameplay|lets play|let s play|playthrough|video game|pc game|rom hack|fan film|fanfilm|fan made|fanmade|parody|tribute|theory|analysis|essay|retrospective|history of|making of|behind the scenes|unboxing|toys?|figures?|cosplay|convention|panel|lost media|creepypasta|meets|crossover|s adventures of|vs|versus|remake|reboot of|live action|musical|on ice|read aloud|audiobook|book|comic|manga|soundtrack|ost|album|song|songs|music video|amv|opening|intro|credits|theme|clip|clips|scene|scenes|moments|compilation of|best of youtube|shorts|tiktok|meme|memes|ytp|poop|uk dvd|uk vhs|pal)\b")
PRE = r"(?:the |disney s |disneys |walt disney s |nickelodeon s |nickelodeon |nick |nicktoons |cartoon network s |cartoon network |cn |fox kids |kids wb |abc |cbs |nbc |pbs |pbs kids |marvel s |dic s |hanna barbera s |warner bros |wb |saban s |jim henson s |the new adventures of |the adventures of |adventures of |the all new |all new |the new |new |tv |vhs |dvd |\d{4} |\[[a-z0-9 ]+\] )*"
NEED = {
 'Dungeons & Dragons': r"cartoon|animated|1983|1984|1985|cbs|s\d{1,2} ?e\d", 'The Legend of Zelda': r"cartoon|animated|1989|super show|dic|s\d{1,2} ?e\d", 'Sonic the Hedgehog': r"satam|animated|cartoon|s\d{1,2} ?e\d|abc|199[34]", 'Adventures of Sonic the Hedgehog': r"", 'Back to the Future': r"animated|cartoon|cbs|s\d{1,2} ?e\d", 'Teen Wolf': r"animated|cartoon|1986|1987|cbs", 'Super Mario World': r"cartoon|animated|s\d{1,2} ?e\d|1991|nbc|complete series", 'Aladdin': r"the series|animated series|tv series|s\d{1,2} ?e\d|disney afternoon", 'Hercules': r"the series|animated series|tv series|disney", 'The Little Mermaid': r"the series|animated series|tv series|s\d{1,2} ?e\d|cbs", 'Mighty Ducks': r"animated|the series|cartoon|199[67]|s\d{1,2} ?e\d|ep \d", 'Earthworm Jim': r"cartoon|animated|s\d{1,2} ?e\d|episode|kids wb|dvd|complete", 'Doug': r"nickelodeon|nick|disney|s\d{1,2} ?e\d|season|complete|brand spanking", 'Fifteen': r"nickelodeon|hillside", 'What Would You Do?': r"nickelodeon|marc summers", 'Ramona': r"1988|sarah polley|pbs", 'Madeline': r"s\d{1,2} ?e\d|season|episode|the new adventures|dic|complete", 'Storytime': r"pbs|kcet|kino", 'Zoom': r"pbs|wgbh", 'Cartoon Network': r"19[89]\d|200[0-4]|with commercials|w commercials|woc|block|broadcast|aired|recording|vhs", 'Toonami': r"19[89]\d|200[0-4]|with commercials|w commercials|woc|broadcast|aired|recording|vhs|midnight run|rising sun", "Kids' WB": r"19[89]\d|200[0-4]|with commercials|w commercials|woc|block|broadcast|aired|recording|vhs", 'Fox Kids': r"19[89]\d|200[0-4]|with commercials|w commercials|woc|block|broadcast|aired|recording|vhs", 'Saturday morning cartoons': r"19[89]\d|200[0-4]|with commercials|w commercials|woc|abc|cbs|nbc|fox|recording|vhs", 'One Saturday Morning': r"abc|disney", 'Power Rangers': r"mighty morphin|zeo|turbo|in space|lost galaxy|lightspeed|time force|wild force|ninja storm|dino thunder|199\d|200[0-4]", 'Goosebumps': r"s\d{1,2} ?e\d|season|episode|fox kids|tv series|complete|vhs", 'Inspector Gadget': r"s\d{1,2} ?e\d|season|episode|complete|198\d|cartoon", 'Samurai Jack': r"s\d{1,2} ?e\d|season [1-4]|episode|complete", 'Kim Possible': r"s\d{1,2} ?e\d|season|episode \d|complete", 'SpongeBob SquarePants': r"s0?[1-3] ?e\d|season [1-3]\b|1999|200[0-4]", 'Alvin and the Chipmunks': r"s\d{1,2} ?e\d|season|episode|198\d|nbc|cartoon|complete", 'Attack of the Killer Tomatoes': r"animated|cartoon|1990|1991|fox|s\d{1,2} ?e\d|the series", 'Beetlejuice': r"animated|cartoon|s\d{1,2} ?e\d|season|episode|the series", 'Free Willy': r"animated|cartoon|s\d{1,2} ?e\d|the series", 'Punky Brewster': r"animated|cartoon|it s punky", 'Dennis the Menace': r"1986|animated|cartoon|dic|s\d{1,2} ?e\d", 'Recess': r"disney|s\d{1,2} ?e\d|season|episode|complete", 'Babar': r"s\d{1,2} ?e\d|season|episode|nelvana|complete|hbo", 'Jem': r"holograms|s\d{1,2} ?e\d|season|episode|complete", 'Care Bears': r"s\d{1,2} ?e\d|season|episode|198\d|dic|nelvana|family", 'Out of the Box': r"playhouse disney|disney", 'The Tick': r"animated|cartoon|199[4-6]|fox|s\d{1,2} ?e\d", 'Digimon': r"adventure|tamers|frontier|digital monsters|s0?[1-4] ?e\d|season [1-4]\b|fox kids|199\d|200[0-3]", 'Yu-Gi-Oh!': r"duel monsters|season [1-4]\b|s0?[1-4] ?e\d|kids wb|200[1-4]", 'Beyblade': r"v force|g revolution|season [1-3]\b|s0?[1-3] ?e\d|200[2-4]", 'Zoids': r"chaotic century|new century|guardian force|fuzors|s\d{1,2} ?e\d",
}
BAD2 = {
 'Power Rangers': r"samurai|rpm|mystic force|spd|s p d|megaforce|jungle fury|overdrive|beast morphers|ninja steel|dino charge|dino fury|cosmic fury|operation overdrive", 'Digimon': r"fusion|ghost game|data squad|xros|savers|appli|universe|storytime|cyber sleuth|survive|tri\b", 'Yu-Gi-Oh!': r"5d|zexal|gx|arc v|vrains|go rush|sevens|abridged|cards", 'Beyblade': r"metal|burst|shogun", 'Alvin and the Chipmunks': r"road chip|meet|squeakquel|chipwrecked|movie|alvinnn", 'Hercules': r"young hercules|legendary journeys|minecraft", 'Aladdin': r"jamillah|tweenies|return of jafar|king of thieves", 'The Little Mermaid': r"little fox|2023", 'Teen Wolf': r"season [1-6]\b.*epis|mtv", 'SpongeBob SquarePants': r"movie|musical", 'Inspector Gadget': r"field trip|gadget 2|biggest caper|last case|2015", 'Doug': r"with doug|and doug|doug show|doug [a-z]+ (show|podcast)", 'Sonic the Hedgehog': r"sonic x|boom|prime|underground|ova|movie|zone|act \d", 'Super Mario World': r"hack|kaizo|smw", 'The Legend of Zelda': r"ocarina|wind waker|twilight|skyward|breath|tears|majora|link to the past|part \d", 'Mighty Ducks': r"game changers|d2|d3", 'Back to the Future': r"part ii|part iii|part 2|part 3|telltale|the game", 'Teacher\'s Pet': r"fifties|trouble with father", 'Recess': r"my recess|school s out", 'Mighty Morphin Power Rangers': r"once and always", 'Static Shock': r"disturbing", 'Hey Arnold!': r"gone to hell",
}
def r2ok(sh, t, ident):
    title, a, b = sh
    ph = sq(title); squeezed = ph.replace(' and ', ' ').replace(' ', '')
    alts = {ph, ph.replace(' and ', ' ')}
    if ph.startswith('the '): alts |= {ph[4:], ph[4:].replace(' and ', ' ')}
    for x in list(alts):
        if x.endswith(' show') and len(x) > 12: alts.add(x[:-5])
        if x.startswith('adventures of ') and len(x) > 22: alts.add(x[14:])
    low = norm(t); st = sq(t); idl = re.sub(r'[^a-z0-9]+', '', str(ident).lower())
    if not low: return False
    m = None
    for x in sorted(alts, key=len, reverse=True):
        m = re.match(PRE + re.escape(x) + r'(?= |$)', st)
        if m: break
    in_i = len(squeezed) >= 9 and idl.startswith(squeezed)
    if not (m or in_i): return False
    rest = st[m.end():] if m else st
    if not (DISC.search(' ' + st + ' ') or (m and rest.strip() == '' and title not in AMB2 and len(ph.split()) >= 3)): return False
    if J2.search(st) or JUNK.search(low) or FOREIGN.search(low) or CODES.search(str(t)): return False
    if re.search(r'\b\d{1,2}[/.-]\d{1,2}[/.-](0[5-9]|1\d|2\d)\b', low): return False
    if MODERN.search(low) and not ERA.search(low): return False
    nd = NEED.get(title)
    if nd and not re.search(nd, st): return False
    bd = BAD2.get(title)
    if bd and re.search(bd, st): return False
    sm = re.search(r'\b(?:season|s)\s?0?(\d{1,2})\b', st)
    if sm and int(sm.group(1)) > (min(b, 2004) - a + 2): return False
    ys = [int(y) for y in ERA.findall(low)]
    if ys and not any(a - 1 <= y <= 2004 for y in ys): return False
    return True
def r2search(sh):
    title, a, b = sh
    ph = sq(title)
    squeezed = ph.replace(' and ', ' ').replace(' ', '')
    qt = title.replace('"', '').replace('!', '').replace('?', '')
    qs = ['mediatype:movies AND title:("' + qt + '")', 'mediatype:movies AND subject:("' + qt + '")']
    if len(squeezed) >= 9:
        base = ph.replace(' and ', ' ')
        v = {squeezed, base.replace(' ', '-'), base.replace(' ', '_'), base.replace(' ', '.')}
        if squeezed.startswith('the') and len(squeezed) >= 12: v |= {squeezed[3:], base[4:].replace(' ', '-'), base[4:].replace(' ', '_'), base[4:].replace(' ', '.')}
        qs.append('mediatype:movies AND identifier:(' + ' OR '.join(x + '*' for x in sorted(v)) + ')')
    items = []; ids = set()
    for q in qs:
        for it in scrape(q):
            if it['identifier'] not in ids: ids.add(it['identifier']); items.append(it)
    keep = []
    for it in items:
        t = it.get('title')
        if isinstance(t, list): t = ' '.join(t)
        if it['identifier'] in have: continue
        lang = it.get('language')
        if isinstance(lang, list): lang = ' '.join(lang)
        if lang and not re.search(r'eng|english|^en\b', str(lang).lower()): continue
        if not r2ok(sh, t, it['identifier']): continue
        it['title'] = t; it['k'] = title; it['yr'] = a
        keep.append(it)
    return title, len(items), keep
r2found = collections.Counter(); r2raw = {}
with ThreadPoolExecutor(8) as ex:
    for title, n, keep in ex.map(r2search, R2):
        r2raw[title] = n
        for it in keep:
            o = seen.get(it['identifier'])
            if o is None:
                seen[it['identifier']] = it; r2found[title] += 1
            elif o['k'] in LUMP: o['k'] = title
        print('route2', title, n, len(keep), 'total', len(seen), flush=True)
cands = list(seen.values())
print('candidates', len(cands), flush=True)
def secs(v):
    try:
        if ':' in str(v):
            s = 0
            for x in str(v).split(':'): s = s * 60 + float(x)
            return s
        return float(v)
    except Exception:
        return 0
RANK = {'h.264 IA': 0, 'h.264': 1, 'MPEG4': 2, '512Kb MPEG4': 3}
why = collections.Counter()
def meta(it):
    j = get('https://archive.org/metadata/' + urllib.parse.quote(it['identifier']))
    if not j or not j.get('files') or j.get('is_dark'): why['dark'] += 1; return None
    m = j.get('metadata', {})
    if str(m.get('access-restricted-item', '')).lower() == 'true': why['restricted'] += 1; return None
    lang = m.get('language', '')
    if isinstance(lang, list): lang = ' '.join(lang)
    if lang and not re.search(r'eng|english|^en\b', str(lang).lower()): why['lang'] += 1; return None
    desc = m.get('description', '')
    if isinstance(desc, list): desc = ' '.join(desc)
    desc = ' '.join(re.sub(r'<[^>]+>', ' ', str(desc)).split())
    subj = m.get('subject', '')
    if isinstance(subj, list): subj = ';'.join(subj)
    if FOREIGN.search(norm(subj)) or FOREIGN.search(norm(desc[:300])): why['foreign'] += 1; return None
    groups = {}
    for f in j['files']:
        if not f.get('name', '').lower().endswith('.mp4'): continue
        key = f.get('original') if f.get('source') == 'derivative' else f['name']
        groups.setdefault(key, []).append(f)
    files = []
    for key, g in groups.items():
        g.sort(key=lambda f: RANK.get(f.get('format', ''), 9))
        b = g[0]
        if RANK.get(b.get('format', ''), 9) == 9: continue
        d = secs(b.get('length') or next((x.get('length') for x in g if x.get('length')), 0))
        if d < 120: continue
        sz = float(b.get('size') or 0)
        if sz and sz / 1e6 / (d / 60) > 30: continue
        files.append([b['name'], round(d), b.get('format', '')])
    if not files: why['nofiles'] += 1; return None
    if sum(f[1] for f in files) < 600: why['short'] += 1; return None
    files.sort(key=lambda f: f[0])
    t = str(m.get('title', '') or it['title'])
    if isinstance(m.get('title'), list): t = ' '.join(m['title'])
    low = norm(t)
    ys = [int(x) for x in ERA.findall(low)]
    d = str(m.get('date', '') or '')
    dy = re.match(r'(\d{4})', d)
    e = ys[0] if ys else (int(dy.group(1)) if dy and 1984 <= int(dy.group(1)) <= 2004 else it['yr'])
    col = m.get('collection', [])
    if isinstance(col, str): col = [col]
    return {'i': it['identifier'], 'q': 'kids', 't': t[:200], 'd': d, 'y': str(m.get('year', '') or ''), 'c': col[:4], 's': str(subj)[:200], 'ds': desc[:400], 'f': files[:60], 'dl': it.get('downloads') or 0, 'k': it['k'], 'e': e}
OF = os.path.join(OUT, 'schoolage.json.gz')
prev = {x['i']: x for x in json.load(gzip.open(OF, 'rt', encoding='utf-8'))} if os.path.exists(OF) else {}
res = []
todo = []
for it in cands:
    p = prev.get(it['identifier'])
    if p:
        p['k'] = it['k']; res.append(p)
    else: todo.append(it)
_ci = set(it['identifier'] for it in cands)
R2D = {x[0]: x for x in R2}
J3 = re.compile(r"\b(nostalgia critic|completionist|speedpaint|lets watch|let s watch|reaction|review|podcast|livestream|gameplay|longplay|lot \d|image gallery|equestria|friendship is magic|mystic force|spd|rpm|megaforce|dino charge|dino fury|ninja steel|aco ninja|battle for the grid|once and always|cbeebies|creature shop challenge|closing credits|years old|honest truth|vs|uk vhs|uk dvd|vhs australia|jetix|surprise \d|tricked|guilty|bdrip|ai upscale|commentary|ranking|top \d+|explained|theory|interview|unboxing|toy|toys|fan made|fanmade|parody|ytp|amv|minecraft|roblox)\b")
def _j3(x): return bool(J3.search(sq(x.get('t', '')))) or bool(MODERN.search(norm(x.get('t', ''))) and not ERA.search(norm(x.get('t', ''))))
res = [x for x in res if x['k'] not in R2D or r2ok(R2D[x['k']], x['t'], x['i'])]
res = [x for x in res if not _j3(x)]
purged = 0
for _i, _p in prev.items():
    if _i in _ci or _i in have: continue
    if _p['k'] in R2D and not r2ok(R2D[_p['k']], _p['t'], _i): purged += 1; continue
    if _j3(_p): purged += 1; continue
    res.append(_p)
print('purged', purged, flush=True)
print('reused', len(res), 'to look up', len(todo), flush=True)
cands = todo
with ThreadPoolExecutor(THREADS) as ex:
    for n, r in enumerate(ex.map(meta, cands)):
        if r: res.append(r)
        if n % 1000 == 0: print('meta', n, len(res), flush=True)
res.sort(key=lambda x: (x['k'], -x['dl']))
with gzip.open(os.path.join(OUT, 'schoolage.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('done', len(res), 'looked up', len(cands), 'dropped', dict(why), flush=True)
tab = collections.defaultdict(lambda: [0, 0, 0])
for x in res:
    r = tab[x['k']]; r[0] += 1; r[1] += len(x['f']); r[2] += sum(f[1] for f in x['f'])
print('SHOW TABLE tag items files hours rawhits kept_after_title')
for sh in S:
    r = tab[sh[0]]
    print('  %-16s %5d %6d %7.1f %7d %6d %s' % (sh[0], r[0], r[1], r[2] / 3600, rawhits.get(sh[0], 0), found[sh[0]], 'ZERO' if not r[0] else ''))
print('ROUTE2 TABLE show items files hours rawhits new_candidates flag')
for sh in R2:
    r = tab[sh[0]]
    print('  %-44s %5d %6d %7.1f %7d %6d %s' % (sh[0], r[0], r[1], r[2] / 3600, r2raw.get(sh[0], 0), r2found[sh[0]], 'MISSING' if not r[0] else 'THIN' if r[1] < 15 else 'FOUND'))
cov = collections.defaultdict(lambda: [0, 0, 0.0])
def _cov(x):
    for sh in R2:
        if r2ok(sh, x.get('t', ''), x.get('i', '')):
            c = cov[sh[0]]; c[0] += 1; c[1] += len(x.get('f') or []); c[2] += sum(f[1] for f in (x.get('f') or [])) / 3600
            return
for _p in glob.glob(os.path.join(OUT, '*.json.gz')):
    if os.path.basename(_p) in ('schoolage.json.gz', 'dates.json.gz', 'epguide.json.gz', 'adsdates.json.gz', 'ads.json.gz', 'movies.json.gz', 'sports.json.gz', 'filler.json.gz'): continue
    try:
        for _x in json.load(gzip.open(_p, 'rt', encoding='utf-8')):
            if isinstance(_x, dict) and 'i' in _x and 'f' in _x: _cov(_x)
    except Exception as _e: print('skip', _p, _e)
for _x in res: _cov(_x)
print('COVERAGE ALL CATALOGS show items files hours flag')
for sh in R2:
    c = cov[sh[0]]
    print('  %-44s %5d %6d %7.1f %s' % (sh[0], c[0], c[1], c[2], 'MISSING' if not c[0] else 'THIN' if c[1] < 15 else 'FOUND'))
print('TOTAL items', len(res), 'files', sum(len(x['f']) for x in res), 'hours', round(sum(sum(f[1] for f in x['f']) for x in res) / 3600))
print('ERA YEARS', sorted(collections.Counter(x['e'] for x in res).items()))
random.seed(7)
print('SAMPLE')
for x in random.sample(res, min(60, len(res))):
    print('  ', x['k'], '|', x['e'], '|', len(x['f']), 'f', round(sum(f[1] for f in x['f']) / 60), 'min |', x['t'][:90], '|', x['i'][:40])
