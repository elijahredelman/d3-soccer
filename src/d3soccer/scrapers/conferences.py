"""
Generic conference registry + standings scraper, generalized from the SCIAC
pilot (see sciac.py, kept as-is for backward compatibility / the original
pilot script). Every conference below was researched and confirmed live
on 2026-09-18: all member schools run the Sidearm Sports platform, so the
same roster/schedule/stats scrapers in sidearm.py work unchanged -- only
the domain changes per school.

Adding a new conference means adding one entry to CONFERENCES with its
standings URL and TEAMS list; no new scraper code needed unless a school
deviates from the standard `/sports/mens-soccer/...` URL pattern (see the
`quirks` notes below for the ones that do).
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from d3soccer.models import StandingRow, Team

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; D3SoccerAppBot/0.1; contact: elijahredelman@gmail.com)"
}
TIMEOUT = 30


# ---------------------------------------------------------------------
# NESCAC -- New England Small College Athletic Conference
# ---------------------------------------------------------------------
NESCAC_TEAMS = [
    Team(name="Amherst", conference="NESCAC", site_domain="athletics.amherst.edu"),
    Team(name="Bates", conference="NESCAC", site_domain="gobatesbobcats.com"),
    Team(name="Bowdoin", conference="NESCAC", site_domain="athletics.bowdoin.edu"),
    Team(name="Colby", conference="NESCAC", site_domain="colbyathletics.com"),
    Team(name="Connecticut College", conference="NESCAC", site_domain="camelathletics.com"),
    Team(name="Hamilton", conference="NESCAC", site_domain="athletics.hamilton.edu"),
    Team(name="Middlebury", conference="NESCAC", site_domain="athletics.middlebury.edu"),
    Team(name="Trinity", conference="NESCAC", site_domain="bantamsports.com"),
    Team(name="Tufts", conference="NESCAC", site_domain="gotuftsjumbos.com"),
    Team(name="Wesleyan", conference="NESCAC", site_domain="athletics.wesleyan.edu"),
    Team(name="Williams", conference="NESCAC", site_domain="ephsports.williams.edu"),
]
# NESCAC has no season-agnostic standings URL (unlike SCIAC's `?path=msoc`)
# -- it's `nescac.com/standings.aspx?standings=<id>` with a numeric id that
# changes every year (2026 season = 404, 2025 = 389, 2024 = 376 -- roughly
# +13-15/year). fetch_nescac_standings() below tries to resolve the current
# id dynamically from the sport hub page before falling back to this
# hardcoded value -- update NESCAC_FALLBACK_STANDINGS_ID each fall if the
# dynamic lookup ever stops working.
NESCAC_FALLBACK_STANDINGS_ID = 404


# ---------------------------------------------------------------------
# UAA -- University Athletic Association
# ---------------------------------------------------------------------
UAA_TEAMS = [
    Team(name="Brandeis", conference="UAA", site_domain="brandeisjudges.com"),
    Team(name="Carnegie Mellon", conference="UAA", site_domain="athletics.cmu.edu"),
    Team(name="Case Western Reserve", conference="UAA", site_domain="athletics.case.edu"),
    Team(name="Chicago", conference="UAA", site_domain="athletics.uchicago.edu"),
    Team(name="Emory", conference="UAA", site_domain="emoryathletics.com"),
    Team(name="NYU", conference="UAA", site_domain="gonyuathletics.com"),
    Team(name="Rochester", conference="UAA", site_domain="uofrathletics.com"),
    Team(name="Washington University in St. Louis", conference="UAA", site_domain="washubears.com"),
]
# Quirk: Carnegie Mellon's fetch was blocked by this session's proxy policy
# (not a real site error) -- search evidence points to an OLDER Sidearm URL
# scheme for this one school: /sports/msoc/<season-slug>/roster instead of
# /sports/mens-soccer/roster. Verify manually before relying on it; the
# other 7 UAA schools are confirmed on the standard pattern.


# ---------------------------------------------------------------------
# MIAC -- Minnesota Intercollegiate Athletic Conference
# ---------------------------------------------------------------------
MIAC_TEAMS = [
    Team(name="Saint John's (MN)", conference="MIAC", site_domain="gojohnnies.com"),
    Team(name="St. Olaf", conference="MIAC", site_domain="athletics.stolaf.edu"),
    Team(name="Bethel (MN)", conference="MIAC", site_domain="athletics.bethel.edu"),
    Team(name="Carleton", conference="MIAC", site_domain="athletics.carleton.edu"),
    Team(name="Macalester", conference="MIAC", site_domain="athletics.macalester.edu"),
    Team(name="Augsburg", conference="MIAC", site_domain="athletics.augsburg.edu"),
    Team(name="Gustavus Adolphus", conference="MIAC", site_domain="gogusties.com"),
    Team(name="Hamline", conference="MIAC", site_domain="hamlineathletics.com"),
    Team(name="Saint Mary's (MN)", conference="MIAC", site_domain="saintmaryssports.com"),
    Team(name="St. Scholastica", conference="MIAC", site_domain="csssaints.com"),
    Team(name="Concordia (Moorhead)", conference="MIAC", site_domain="gocobbers.com"),
]
# Note: St. Thomas (MN) was removed from the MIAC (2019, effective ~2021)
# and has fully transitioned to D1 -- correctly excluded here, not a D3 team.
# Quirk: Concordia-Moorhead (gocobbers.com) 403'd every automated fetch in
# research (looks like bot/WAF protection, not a platform difference) --
# verify manually; search suggests it may still be on an older
# /sports/msoc/index-style URL rather than /sports/mens-soccer/....


# ---------------------------------------------------------------------
# WIAC -- Wisconsin Intercollegiate Athletic Conference
# (only 6 of 8 members currently sponsor varsity men's soccer)
# ---------------------------------------------------------------------
WIAC_TEAMS = [
    Team(name="Wisconsin-Eau Claire", conference="WIAC", site_domain="blugolds.com"),
    Team(name="Wisconsin-Whitewater", conference="WIAC", site_domain="uwwsports.com"),
    Team(name="Wisconsin-Platteville", conference="WIAC", site_domain="letsgopioneers.com"),
    Team(name="Wisconsin-Stevens Point", conference="WIAC", site_domain="athletics.uwsp.edu"),
    Team(name="Wisconsin-Stout", conference="WIAC", site_domain="stoutbluedevils.com"),
    Team(name="Wisconsin-River Falls", conference="WIAC", site_domain="uwrfsports.com"),
]
# UW-La Crosse: club-only, no varsity WIAC men's soccer program -- excluded.
# UW-Oshkosh: dropped the program in 2015, reinstatement targeted for
# fall 2027 -- not yet competing, excluded until then.


# ---------------------------------------------------------------------
# Northwest Conference (NWC)
# ---------------------------------------------------------------------
NWC_TEAMS = [
    Team(
        name="George Fox", conference="Northwest Conference", site_domain="athletics.georgefox.edu"
    ),
    Team(name="Lewis & Clark", conference="Northwest Conference", site_domain="golcathletics.com"),
    Team(name="Linfield", conference="Northwest Conference", site_domain="golinfieldwildcats.com"),
    Team(name="Pacific (OR)", conference="Northwest Conference", site_domain="goboxers.com"),
    Team(name="Pacific Lutheran", conference="Northwest Conference", site_domain="golutes.com"),
    Team(name="Puget Sound", conference="Northwest Conference", site_domain="loggerathletics.com"),
    Team(name="Whitman", conference="Northwest Conference", site_domain="whitmanblues.com"),
    Team(name="Whitworth", conference="Northwest Conference", site_domain="whitworthpirates.com"),
    Team(name="Willamette", conference="Northwest Conference", site_domain="www.wubearcats.com"),
]
# Quirks: Whitman uses /sports/msoc/... (not /sports/mens-soccer/...).
# Willamette uses /sports/msoc/<YYYY-YY>/... (abbreviated code + a
# hyphenated season slug, not a bare year) and 403'd automated fetches in
# research -- both need hand verification / a small per-school override
# before the standard sidearm.py functions will work on them.


# ---------------------------------------------------------------------
# Liberty League
# ---------------------------------------------------------------------
LIBERTY_LEAGUE_TEAMS = [
    Team(name="Bard", conference="Liberty League", site_domain="bardathletics.com"),
    Team(name="Clarkson", conference="Liberty League", site_domain="clarksonathletics.com"),
    Team(name="Hobart", conference="Liberty League", site_domain="hwsathletics.com"),
    Team(name="Ithaca", conference="Liberty League", site_domain="athletics.ithaca.edu"),
    Team(name="RPI", conference="Liberty League", site_domain="rpiathletics.com"),
    Team(name="RIT", conference="Liberty League", site_domain="ritathletics.com"),
    Team(name="St. Lawrence", conference="Liberty League", site_domain="saintsathletics.com"),
    Team(name="Skidmore", conference="Liberty League", site_domain="skidmoreathletics.com"),
    Team(name="Union", conference="Liberty League", site_domain="unionathletics.com"),
    Team(name="Vassar", conference="Liberty League", site_domain="www.vassarathletics.com"),
]
# Note: Rochester is a Liberty League member but its men's soccer plays in
# UAA (already covered there) -- correctly excluded here. Hamilton left for
# NESCAC in 2011 (already covered there) -- also excluded.

# ---------------------------------------------------------------------
# Centennial Conference
# ---------------------------------------------------------------------
CENTENNIAL_TEAMS = [
    Team(
        name="Dickinson",
        conference="Centennial",
        site_domain="dickinsonathletics.com",
        sport_slug="msoc",
    ),
    Team(name="Franklin & Marshall", conference="Centennial", site_domain="godiplomats.com"),
    Team(name="Gettysburg", conference="Centennial", site_domain="gettysburgsports.com"),
    Team(name="Haverford", conference="Centennial", site_domain="haverfordathletics.com"),
    Team(name="Johns Hopkins", conference="Centennial", site_domain="hopkinssports.com"),
    Team(name="McDaniel", conference="Centennial", site_domain="mcdanielathletics.com"),
    Team(name="Muhlenberg", conference="Centennial", site_domain="muhlenbergsports.com"),
    Team(name="Swarthmore", conference="Centennial", site_domain="swarthmoreathletics.com"),
    Team(name="Ursinus", conference="Centennial", site_domain="ursinusathletics.com"),
    Team(name="Washington College", conference="Centennial", site_domain="washcollsports.com"),
]
# Quirk: Dickinson's canonical URL uses the short "msoc" sport-slug instead
# of "mens-soccer" -- not yet handled by sidearm.py, expect this one to
# fail until a per-school override or a slug-fallback is added.

# ---------------------------------------------------------------------
# Empire 8
# ---------------------------------------------------------------------
EMPIRE8_TEAMS = [
    Team(name="Alfred", conference="Empire 8", site_domain="gosaxons.com"),
    Team(name="Elmira", conference="Empire 8", site_domain="athletics.elmira.edu"),
    Team(name="Hartwick", conference="Empire 8", site_domain="hartwickhawks.com"),
    Team(name="Houghton", conference="Empire 8", site_domain="athletics.houghton.edu"),
    Team(name="Keuka", conference="Empire 8", site_domain="keukaathletics.com"),
    Team(name="Nazareth", conference="Empire 8", site_domain="nazathletics.com"),
    Team(name="Russell Sage", conference="Empire 8", site_domain="www.sagegators.com"),
    Team(name="St. John Fisher", conference="Empire 8", site_domain="sjfathletics.com"),
    Team(name="SUNY Brockport", conference="Empire 8", site_domain="gobrockport.com"),
    Team(name="SUNY Geneseo", conference="Empire 8", site_domain="geneseoknights.com"),
    Team(name="SUNY Poly", conference="Empire 8", site_domain="wildcats.sunypoly.edu"),
    Team(name="Utica", conference="Empire 8", site_domain="uticapioneers.com"),
]
# Quirk: Russell Sage (sagegators.com) uses an older /sports/msoc/<season>/
# URL scheme and blocked automated fetches during research (403) -- expect
# this one to fail until verified/overridden. Keuka is leaving Empire 8
# for the AMCC after 2026-27 -- fine for this season, revisit next year.

# ---------------------------------------------------------------------
# Ohio Athletic Conference (OAC)
# ---------------------------------------------------------------------
OAC_TEAMS = [
    Team(name="Baldwin Wallace", conference="OAC", site_domain="bwyellowjackets.com"),
    Team(name="Capital", conference="OAC", site_domain="athletics.capital.edu"),
    Team(name="Heidelberg", conference="OAC", site_domain="bergathletics.com"),
    Team(name="Marietta", conference="OAC", site_domain="pioneers.marietta.edu"),
    Team(name="Mount Union", conference="OAC", site_domain="athletics.mountunion.edu"),
    Team(name="Muskingum", conference="OAC", site_domain="fightingmuskies.com"),
    Team(name="Ohio Northern", conference="OAC", site_domain="onusports.com"),
    Team(name="Otterbein", conference="OAC", site_domain="otterbeincardinals.com"),
    Team(name="Wilmington", conference="OAC", site_domain="wilmingtonquakers.com"),
]
# Note: John Carroll left OAC for NCAC in 2025 (now listed under NCAC
# instead). Wittenberg/Ohio Wesleyan are NCAC, not OAC -- corrected from
# an initial bad assumption. Quirk: Muskingum and Ohio Northern both
# blocked automated fetches (403) and likely use the older
# /sports/msoc/<season-slug>/ URL scheme -- expect these two to fail
# until verified/overridden.

# ---------------------------------------------------------------------
# North Coast Athletic Conference (NCAC)
# ---------------------------------------------------------------------
NCAC_TEAMS = [
    Team(name="Denison", conference="NCAC", site_domain="bigred.denison.edu"),
    Team(name="DePauw", conference="NCAC", site_domain="depauwtigers.com"),
    Team(name="John Carroll", conference="NCAC", site_domain="jcusports.com"),
    Team(name="Kenyon", conference="NCAC", site_domain="athletics.kenyon.edu"),
    Team(name="Oberlin", conference="NCAC", site_domain="goyeo.com"),
    Team(name="Ohio Wesleyan", conference="NCAC", site_domain="battlingbishops.com"),
    Team(name="Wabash", conference="NCAC", site_domain="sports.wabash.edu"),
    Team(name="Wittenberg", conference="NCAC", site_domain="wittenbergtigers.com"),
    Team(name="Wooster", conference="NCAC", site_domain="woosterathletics.com"),
]
# Quirk: Wittenberg blocked automated fetches (403) and appears to use the
# older /sports/msoc/index URL scheme -- expect this one to fail until
# verified/overridden. Allegheny is PAC, not NCAC; Hiram closed in 2023 --
# both correctly excluded.

# ---------------------------------------------------------------------
# New Jersey Athletic Conference (NJAC)
# ---------------------------------------------------------------------
NJAC_TEAMS = [
    Team(name="Kean", conference="NJAC", site_domain="keanathletics.com"),
    Team(name="Montclair State", conference="NJAC", site_domain="montclairathletics.com"),
    Team(name="Ramapo", conference="NJAC", site_domain="ramapoathletics.com"),
    Team(name="Rowan", conference="NJAC", site_domain="www.rowanathletics.com"),
    Team(name="Rutgers-Camden", conference="NJAC", site_domain="scarletraptors.com"),
    Team(name="Rutgers-Newark", conference="NJAC", site_domain="rutgersnewarkathletics.com"),
    Team(name="SUNY New Paltz", conference="NJAC", site_domain="nphawks.com"),
    Team(name="Stockton", conference="NJAC", site_domain="stocktonathletics.com"),
    Team(name="TCNJ", conference="NJAC", site_domain="tcnjathletics.com"),
    Team(name="William Paterson", conference="NJAC", site_domain="www.wpupioneers.com"),
]
# Note: New Jersey City University dropped out of the NJAC (no longer a
# member) -- correctly excluded. Quirk: William Paterson's roster page is
# blocked by robots.txt for automated fetches -- expect this one to fail.

# ---------------------------------------------------------------------
# NEWMAC (New England Women's and Men's Athletic Conference)
# ---------------------------------------------------------------------
NEWMAC_TEAMS = [
    Team(name="Babson", conference="NEWMAC", site_domain="babsonathletics.com"),
    Team(name="Clark University", conference="NEWMAC", site_domain="clarkathletics.com"),
    Team(name="Coast Guard", conference="NEWMAC", site_domain="coastguardathletics.com"),
    Team(name="Emerson", conference="NEWMAC", site_domain="emersonlions.com"),
    Team(name="MIT", conference="NEWMAC", site_domain="mitathletics.com"),
    Team(name="Salve Regina", conference="NEWMAC", site_domain="salveathletics.com"),
    Team(
        name="Springfield College", conference="NEWMAC", site_domain="springfieldcollegepride.com"
    ),
    Team(name="Wheaton (MA)", conference="NEWMAC", site_domain="wheatoncollegelyons.com"),
    Team(name="WPI", conference="NEWMAC", site_domain="athletics.wpi.edu"),
]
# Note: Mount Holyoke/Smith/Wellesley are women's colleges, no men's
# soccer -- correctly excluded. Watch for name collisions: "Clark" here is
# Clark University MA (clarkathletics.com), not Clark College WA; "Wheaton"
# here is Wheaton MA (wheatoncollegelyons.com), not Wheaton IL.


# ---------------------------------------------------------------------
# Little East Conference (LEC)
# ---------------------------------------------------------------------
LEC_TEAMS = [
    Team(name="Eastern Connecticut State", conference="LEC", site_domain="gowarriorathletics.com"),
    Team(name="Keene State", conference="LEC", site_domain="keeneowls.com"),
    Team(name="Plymouth State", conference="LEC", site_domain="athletics.plymouth.edu"),
    Team(name="Rhode Island College", conference="LEC", site_domain="goanchormen.com"),
    Team(name="UMass Boston", conference="LEC", site_domain="beaconsathletics.com"),
    Team(name="UMass Dartmouth", conference="LEC", site_domain="corsairathletics.com"),
    Team(name="Southern Maine", conference="LEC", site_domain="southernmainehuskies.com"),
    Team(name="Vermont State Castleton", conference="LEC", site_domain="castletonsports.com"),
    Team(name="Western Connecticut", conference="LEC", site_domain="westconnathletics.com"),
]
# Note: VTSU Castleton leaves LEC for MASCAC starting 2027-28 -- fine for this season.

# ---------------------------------------------------------------------
# North Atlantic Conference (NAC)
# ---------------------------------------------------------------------
NAC_TEAMS = [
    Team(name="Thomas College", conference="NAC", site_domain="thomasathletics.com"),
    Team(name="Maine Maritime", conference="NAC", site_domain="marinersports.org"),
    Team(name="Husson", conference="NAC", site_domain="hussoneagles.com"),
    Team(name="Maine-Presque Isle", conference="NAC", site_domain="owls.umpi.edu"),
    Team(name="Maine-Farmington", conference="NAC", site_domain="goumfbeavers.com"),
    Team(name="Vermont State Johnson", conference="NAC", site_domain="nvubadgers.com"),
    Team(name="Lesley", conference="NAC", site_domain="lesleyathletics.com"),
    Team(name="Vermont State Lyndon", conference="NAC", site_domain="vtsuhornets.com"),
]
# Note: NAC dropped to 8 members for 2026-27 -- SUNY Cobleskill/Delhi moved up to SUNYAC.

# ---------------------------------------------------------------------
# Massachusetts State Collegiate Athletic Conference (MASCAC)
# ---------------------------------------------------------------------
MASCAC_TEAMS = [
    Team(name="Bridgewater State", conference="MASCAC", site_domain="bsubears.com"),
    Team(name="Fitchburg State", conference="MASCAC", site_domain="fitchburgfalcons.com"),
    Team(name="Framingham State", conference="MASCAC", site_domain="fsurams.com"),
    Team(
        name="Massachusetts College of Liberal Arts",
        conference="MASCAC",
        site_domain="athletics.mcla.edu",
    ),
    Team(name="Massachusetts Maritime", conference="MASCAC", site_domain="mmabucs.com"),
    Team(name="Salem State", conference="MASCAC", site_domain="salemstatevikings.com"),
    Team(name="Worcester State", conference="MASCAC", site_domain="wsulancers.com"),
]
# Note: Westfield State's domain could not be verified -- add once confirmed. Anna Maria
# closed and is excluded. mascac.com blocks automated fetches (403) -- standings URL below
# is the conventional pattern, unverified.

# ---------------------------------------------------------------------
# Skyline Conference
# ---------------------------------------------------------------------
SKYLINE_TEAMS = [
    Team(name="Manhattanville", conference="Skyline", site_domain="govaliants.com"),
    Team(name="Mount Saint Mary", conference="Skyline", site_domain="msmcknights.com"),
    Team(name="Mount Saint Vincent", conference="Skyline", site_domain="cmsvathletics.com"),
    Team(name="Merchant Marine (USMMA)", conference="Skyline", site_domain="usmmasports.com"),
    Team(name="Sarah Lawrence", conference="Skyline", site_domain="gogryphons.com"),
    Team(name="Farmingdale State", conference="Skyline", site_domain="farmingdalesports.com"),
    Team(name="SUNY Old Westbury", conference="Skyline", site_domain="oldwestburypanthers.com"),
    Team(name="Maritime College (SUNY)", conference="Skyline", site_domain="maritimeathletics.com"),
    Team(name="Yeshiva", conference="Skyline", site_domain="yumacs.com"),
    Team(name="St. Joseph's-Long Island", conference="Skyline", site_domain="sjliathletics.com"),
    Team(name="Purchase College", conference="Skyline", site_domain="purchasecollegeathletics.com"),
    Team(name="St. Joseph's-Brooklyn", conference="Skyline", site_domain="sjbkathletics.com"),
]

# ---------------------------------------------------------------------
# State University of New York Athletic Conference (SUNYAC)
# ---------------------------------------------------------------------
SUNYAC_TEAMS = [
    Team(name="Alfred State", conference="SUNYAC", site_domain="alfredstateathletics.com"),
    Team(name="Buffalo State", conference="SUNYAC", site_domain="buffalostateathletics.com"),
    Team(name="SUNY Canton", conference="SUNYAC", site_domain="rooathletics.com"),
    Team(name="SUNY Cobleskill", conference="SUNYAC", site_domain="fightingtigers.cobleskill.edu"),
    Team(name="SUNY Cortland", conference="SUNYAC", site_domain="cortlandreddragons.com"),
    Team(name="SUNY Delhi", conference="SUNYAC", site_domain="delhibroncos.com"),
    Team(name="SUNY Fredonia", conference="SUNYAC", site_domain="fredoniabluedevils.com"),
    Team(name="SUNY Morrisville", conference="SUNYAC", site_domain="morrisvillemustangs.com"),
    Team(name="SUNY Oneonta", conference="SUNYAC", site_domain="oneontaathletics.com"),
    Team(name="SUNY Oswego", conference="SUNYAC", site_domain="oswegolakers.com"),
    Team(name="SUNY Plattsburgh", conference="SUNYAC", site_domain="gocardinalsports.com"),
    Team(name="SUNY Potsdam", conference="SUNYAC", site_domain="potsdambears.com"),
]
# Note: Alfred State, Cobleskill, Delhi are new full members for 2026-27 (up from NAC).
# sunyacsports.com blocks automated fetches (403); may use year-slugged msoc paths.

# ---------------------------------------------------------------------
# Great Northeast Athletic Conference (GNAC)
# ---------------------------------------------------------------------
GNAC_TEAMS = [
    Team(name="Colby-Sawyer", conference="GNAC", site_domain="colby-sawyerathletics.com"),
    Team(name="Dean College", conference="GNAC", site_domain="deanbulldogs.com"),
    Team(name="Elms College", conference="GNAC", site_domain="athletics.elms.edu"),
    Team(name="Emmanuel College", conference="GNAC", site_domain="goecsaints.com"),
    Team(name="Lasell", conference="GNAC", site_domain="laserpride.lasell.edu"),
    Team(name="New England College", conference="GNAC", site_domain="athletics.nec.edu"),
    Team(name="Norwich", conference="GNAC", site_domain="norwichathletics.com"),
    Team(name="University of Saint Joseph (CT)", conference="GNAC", site_domain="usjbluejays.com"),
    Team(name="Albertus Magnus", conference="GNAC", site_domain="albertusfalcons.com"),
    Team(name="Mitchell College", conference="GNAC", site_domain="mitchellathletics.com"),
    Team(name="Regis College", conference="GNAC", site_domain="goregispride.com"),
    Team(name="Rivier University", conference="GNAC", site_domain="rivierathletics.com"),
    Team(name="Saint Joseph's College of Maine", conference="GNAC", site_domain="gomonks.com"),
]
# Note: Simmons is a GNAC member but women's-only, no men's soccer -- excluded (important trap,
# it shows a false "soccer: yes" in generic sponsorship tables). The 5 domains above (Albertus
# Magnus, Mitchell, Regis, Rivier, Saint Joseph's ME) were found via web search 2026-10-06, not
# independently fetched/verified against a live roster page yet -- flag for a spot-check on the
# next real pull before trusting them fully. thegnac.com itself still blocks automated fetches.

# ---------------------------------------------------------------------
# City University of New York Athletic Conference (CUNYAC)
# ---------------------------------------------------------------------
CUNYAC_TEAMS = [
    Team(name="Baruch College", conference="CUNYAC", site_domain="athletics.baruch.cuny.edu"),
    Team(name="Brooklyn College", conference="CUNYAC", site_domain="brooklyncollegeathletics.com"),
    Team(name="City College of New York", conference="CUNYAC", site_domain="ccnyathletics.com"),
    Team(name="Hunter College", conference="CUNYAC", site_domain="huntercollegeathletics.com"),
    Team(name="John Jay College", conference="CUNYAC", site_domain="johnjayathletics.com"),
    Team(name="Lehman College", conference="CUNYAC", site_domain="lehmanathletics.com"),
    Team(name="Medgar Evers College", conference="CUNYAC", site_domain="mecathletics.com"),
    Team(name="York College (CUNY)", conference="CUNYAC", site_domain="yorkathletics.com"),
]
# Note: don't confuse with York College of Pennsylvania (MAC Commonwealth) or York County CC.
# CUNYAC's community-college members play NJCAA, not NCAA D3 -- excluded.

# ---------------------------------------------------------------------
# United East Conference
# ---------------------------------------------------------------------
UNITED_EAST_TEAMS = [
    Team(name="Cairn University", conference="UNITED_EAST", site_domain="cairnhighlanders.com"),
    Team(name="Gallaudet University", conference="UNITED_EAST", site_domain="gallaudetbison.com"),
    Team(name="Keystone College", conference="UNITED_EAST", site_domain="gokcgiants.com"),
    Team(name="Lancaster Bible College", conference="UNITED_EAST", site_domain="lbcchargers.com"),
    Team(
        name="Notre Dame of Maryland University",
        conference="UNITED_EAST",
        site_domain="notredamegators.com",
    ),
    Team(
        name="Pennsylvania College of Technology",
        conference="UNITED_EAST",
        site_domain="pctwildcats.com",
    ),
    Team(name="Penn State Abington", conference="UNITED_EAST", site_domain="abingtonsports.com"),
    Team(name="Penn State Berks", conference="UNITED_EAST", site_domain="psuberksathletics.com"),
    Team(
        name="Penn State Brandywine",
        conference="UNITED_EAST",
        site_domain="psubrandywineathletics.com",
        sport_slug="msoc",
    ),
    Team(
        name="Penn State Harrisburg",
        conference="UNITED_EAST",
        site_domain="psuharrisburgsports.com",
        sport_slug="msoc",
    ),
    Team(
        name="St. Mary's College of Maryland",
        conference="UNITED_EAST",
        site_domain="smcmathletics.com",
    ),
    Team(name="Wilson College", conference="UNITED_EAST", site_domain="wilsonphoenix.com"),
]
# Note: Cedar Crest is women's-soccer-only -- excluded. University of Valley Forge closed
# summer 2026 -- excluded.

# ---------------------------------------------------------------------
# Atlantic East Conference
# ---------------------------------------------------------------------
ATLANTIC_EAST_TEAMS = [
    Team(
        name="Centenary University", conference="ATLANTIC_EAST", site_domain="centenarycyclones.com"
    ),
    Team(
        name="Gwynedd Mercy University",
        conference="ATLANTIC_EAST",
        site_domain="gwyneddathletics.com",
    ),
    Team(name="Immaculata University", conference="ATLANTIC_EAST", site_domain="gomightymacs.com"),
    Team(
        name="Marymount University", conference="ATLANTIC_EAST", site_domain="marymountsaints.com"
    ),
    Team(name="Pratt Institute", conference="ATLANTIC_EAST", site_domain="goprattgo.com"),
    Team(
        name="Saint Elizabeth University", conference="ATLANTIC_EAST", site_domain="seueagles.com"
    ),
]
# Note: Marywood and Neumann moved OUT to MAC Freedom/Commonwealth for 2026 -- trust the
# live standings page over stale Wikipedia listings that still show them here.

# ---------------------------------------------------------------------
# MAC Commonwealth (Middle Atlantic Conferences -- men's soccer division)
# ---------------------------------------------------------------------
MAC_COMMONWEALTH_TEAMS = [
    Team(
        name="Albright College", conference="MAC_COMMONWEALTH", site_domain="albrightathletics.com"
    ),
    Team(
        name="Alvernia University",
        conference="MAC_COMMONWEALTH",
        site_domain="athletics.alvernia.edu",
    ),
    Team(
        name="Eastern University", conference="MAC_COMMONWEALTH", site_domain="goeasterneagles.com"
    ),
    Team(name="Hood College", conference="MAC_COMMONWEALTH", site_domain="hoodathletics.com"),
    Team(name="Messiah University", conference="MAC_COMMONWEALTH", site_domain="gomessiah.com"),
    Team(
        name="Neumann University", conference="MAC_COMMONWEALTH", site_domain="neumannathletics.com"
    ),
    Team(
        name="Stevenson University",
        conference="MAC_COMMONWEALTH",
        site_domain="gomustangsports.com",
    ),
    Team(name="Widener University", conference="MAC_COMMONWEALTH", site_domain="widenerpride.com"),
    Team(
        name="York College of Pennsylvania",
        conference="MAC_COMMONWEALTH",
        site_domain="ycpspartans.com",
    ),
]
# Note: men's soccer at "MAC" is genuinely split into 2 divisions (Commonwealth/Freedom),
# unlike some other MAC sports that combine them -- confirmed via gomacsports.com standings
# showing two separate tables. Neumann joined from Atlantic East for 2026.

# ---------------------------------------------------------------------
# MAC Freedom (Middle Atlantic Conferences -- men's soccer division)
# ---------------------------------------------------------------------
MAC_FREEDOM_TEAMS = [
    Team(name="Arcadia University", conference="MAC_FREEDOM", site_domain="arcadiaknights.com"),
    Team(
        name="Delaware Valley University",
        conference="MAC_FREEDOM",
        site_domain="athletics.delval.edu",
    ),
    Team(name="DeSales University", conference="MAC_FREEDOM", site_domain="athletics.desales.edu"),
    Team(
        name="Fairleigh Dickinson University-Florham",
        conference="MAC_FREEDOM",
        site_domain="fdudevils.com",
    ),
    Team(name="King's College", conference="MAC_FREEDOM", site_domain="kingscollegeathletics.com"),
    Team(name="Lebanon Valley College", conference="MAC_FREEDOM", site_domain="godutchmen.com"),
    Team(name="Marywood University", conference="MAC_FREEDOM", site_domain="marywoodpacers.com"),
    Team(
        name="Misericordia University",
        conference="MAC_FREEDOM",
        site_domain="athletics.misericordia.edu",
    ),
    Team(
        name="Stevens Institute of Technology",
        conference="MAC_FREEDOM",
        site_domain="stevensducks.com",
    ),
]
# Note: don't confuse FDU-Florham (D3, fdudevils.com) with the main FDU Knights D1 site.
# Marywood joined from Atlantic East for 2026.

# ---------------------------------------------------------------------
# Landmark Conference
# ---------------------------------------------------------------------
LANDMARK_TEAMS = [
    Team(
        name="Catholic University of America",
        conference="LANDMARK",
        site_domain="catholicathletics.com",
    ),
    Team(name="Drew University", conference="LANDMARK", site_domain="drewrangers.com"),
    Team(name="Elizabethtown College", conference="LANDMARK", site_domain="etownbluejays.com"),
    Team(name="Goucher College", conference="LANDMARK", site_domain="athletics.goucher.edu"),
    Team(name="Juniata College", conference="LANDMARK", site_domain="juniatasports.net"),
    Team(name="Lycoming College", conference="LANDMARK", site_domain="lycomingathletics.com"),
    Team(name="Moravian University", conference="LANDMARK", site_domain="moraviansports.com"),
    Team(
        name="University of Scranton", conference="LANDMARK", site_domain="athletics.scranton.edu"
    ),
    Team(name="Susquehanna University", conference="LANDMARK", site_domain="suriverhawks.com"),
    Team(name="Wilkes University", conference="LANDMARK", site_domain="gowilkesu.com"),
]
# Note: Juniata and Moravian sites block automated fetches (403) -- domains confirmed via
# other sources, expect these two to need special handling.

# ---------------------------------------------------------------------
# Allegheny Mountain Collegiate Conference (AMCC)
# ---------------------------------------------------------------------
AMCC_TEAMS = [
    Team(name="Carlow University", conference="AMCC", site_domain="athletics.carlow.edu"),
    Team(name="Hilbert College", conference="AMCC", site_domain="hilberthawks.com"),
    Team(name="La Roche University", conference="AMCC", site_domain="larochesports.com"),
    Team(name="Mount Aloysius College", conference="AMCC", site_domain="mountieathletics.com"),
    Team(
        name="Penn State Altoona",
        conference="AMCC",
        site_domain="psaltoonalions.com",
        sport_slug="msoc",
    ),
    Team(name="Penn State Behrend", conference="AMCC", site_domain="psblions.com"),
    Team(
        name="University of Pittsburgh at Bradford",
        conference="AMCC",
        site_domain="athletics.pittbradford.org",
        sport_slug="msoc",
    ),
    Team(
        name="University of Pittsburgh at Greensburg",
        conference="AMCC",
        site_domain="pittgreensburgathletics.com",
    ),
]
# Note: amccsports.org blocks automated fetches (403) -- standings URL below is the
# conventional pattern, unverified. Penn State Behrend may run PrestoSports instead of
# Sidearm -- verify.

# ---------------------------------------------------------------------
# Presidents' Athletic Conference (PAC)
# ---------------------------------------------------------------------
PAC_TEAMS = [
    Team(name="Allegheny College", conference="PAC", site_domain="alleghenygators.com"),
    Team(name="Bethany College", conference="PAC", site_domain="bethanybison.com"),
    Team(name="Chatham University", conference="PAC", site_domain="gochathamcougars.com"),
    Team(name="Grove City College", conference="PAC", site_domain="athletics.gcc.edu"),
    Team(name="Hiram College", conference="PAC", site_domain="hiramterriers.com"),
    Team(name="Thiel College", conference="PAC", site_domain="thielathletics.com"),
    Team(name="Washington & Jefferson College", conference="PAC", site_domain="gopresidents.com"),
    Team(name="Waynesburg University", conference="PAC", site_domain="waynesburgsports.com"),
    Team(name="Franciscan University", conference="PAC", site_domain="franciscanathletics.com"),
    Team(name="Geneva College", conference="PAC", site_domain="athletics.geneva.edu"),
    Team(name="Saint Vincent College", conference="PAC", site_domain="athletics.stvincent.edu"),
    Team(
        name="Westminster College (PA)", conference="PAC", site_domain="athletics.westminster.edu"
    ),
    Team(name="Saint Francis University (PA)", conference="PAC", site_domain="sfuathletics.com"),
]
# Note: Hiram returned to PAC for 2025-26 after 35 years away. The 5 domains above (Franciscan,
# Geneva, Saint Vincent, Westminster PA, Saint Francis PA) found via web search 2026-10-06, not
# independently fetched/verified yet -- spot-check on the next real pull. Saint Francis (PA) is
# transitioning D1->D3, plays in 2026 standings but not championship-eligible until 2026-27.

# ---------------------------------------------------------------------
# Old Dominion Athletic Conference (ODAC)
# ---------------------------------------------------------------------
ODAC_TEAMS = [
    Team(name="Bridgewater College", conference="ODAC", site_domain="bridgewatereagles.com"),
    Team(name="Eastern Mennonite University", conference="ODAC", site_domain="emuroyals.com"),
    Team(name="Guilford College", conference="ODAC", site_domain="guilfordquakers.com"),
    Team(name="University of Lynchburg", conference="ODAC", site_domain="lynchburgsports.com"),
    Team(name="Randolph-Macon College", conference="ODAC", site_domain="rmcathletics.com"),
    Team(name="Roanoke College", conference="ODAC", site_domain="roanokemaroons.com"),
    Team(name="Shenandoah University", conference="ODAC", site_domain="suhornets.com"),
    Team(name="Washington and Lee University", conference="ODAC", site_domain="generalssports.com"),
    Team(name="Virginia Wesleyan University", conference="ODAC", site_domain="vwuathletics.com"),
]
# Note: Hollins and Sweet Briar are ODAC members but women's colleges, no men's soccer --
# excluded. Virginia Wesleyan is renaming to Batten University (effective ~mid-2026) -- same
# program, domain still vwuathletics.com as of this search (2026-10-06); rename the Team entry
# once the athletics site itself switches domains, don't rename pre-emptively. Still could not
# find dedicated athletics domains for Averett, Hampden-Sydney, or Randolph College (all three
# appear to run on PrestoSports/d3hoops-hosted pages rather than their own branded domain, or
# search just didn't surface it) -- add once confirmed via odaconline.com team links.

# ---------------------------------------------------------------------
# Southern Athletic Association (SAA)
# ---------------------------------------------------------------------
SAA_TEAMS = [
    Team(name="Berry College", conference="SAA", site_domain="berryvikings.com"),
    Team(name="Centre College", conference="SAA", site_domain="centrecolonels.com"),
    Team(name="Maryville College", conference="SAA", site_domain="mcscots.com"),
    Team(name="Millsaps College", conference="SAA", site_domain="gomajors.com"),
    Team(name="Oglethorpe University", conference="SAA", site_domain="gopetrels.com"),
    Team(name="Rhodes College", conference="SAA", site_domain="rhodeslynx.com"),
    Team(
        name="Sewanee: The University of the South",
        conference="SAA",
        site_domain="sewaneetigers.com",
    ),
    Team(name="Southwestern University", conference="SAA", site_domain="southwesternpirates.com"),
    Team(name="Trinity University", conference="SAA", site_domain="trinitytigers.com"),
]
# Note: Trinity (TX) and Southwestern moved here from SCAC after 2024-25 -- don't double-list.
# Don't confuse with the unrelated NAIA "Southern States Athletic Conference" (also "SSAC").

# ---------------------------------------------------------------------
# Southern Collegiate Athletic Conference (SCAC)
# ---------------------------------------------------------------------
SCAC_TEAMS = [
    Team(name="Austin College", conference="SCAC", site_domain="acathletics.com"),
    Team(name="Centenary College of Louisiana", conference="SCAC", site_domain="gocentenary.com"),
    Team(name="Colorado College", conference="SCAC", site_domain="cctigers.com"),
    Team(name="Schreiner University", conference="SCAC", site_domain="schreinermountaineers.com"),
    Team(name="Texas Lutheran University", conference="SCAC", site_domain="tlubulldogs.com"),
    Team(
        name="Concordia University Texas", conference="SCAC", site_domain="athletics.concordia.edu"
    ),
    Team(name="University of Dallas", conference="SCAC", site_domain="dallas.prestosports.com"),
    Team(name="Hendrix College", conference="SCAC", site_domain="hendrixwarriors.com"),
    Team(name="LeTourneau University", conference="SCAC", site_domain="letuathletics.com"),
    Team(name="University of the Ozarks", conference="SCAC", site_domain="uofoathletics.com"),
    Team(name="University of St. Thomas (Houston)", conference="SCAC", site_domain="ustcelts.com"),
]
# Note: scacsports.com and a couple of member sites (gocentenary.com, schreinermountaineers.com)
# block automated fetches (403). McMurry already listed separately under ASC (rejoins there for
# 2026-27) -- don't double-list it here too. The 6 domains above found via web search 2026-10-06,
# not independently fetched/verified -- spot-check on the next real pull. University of Dallas
# runs on PrestoSports (dallas.prestosports.com), not Sidearm -- its roster/schedule/stats pages
# won't match sidearm.py's URL pattern or HTML parsers; needs its own parser path, standings-only
# for now. Trinity/Southwestern moved out to SAA.

# ---------------------------------------------------------------------
# USA South Athletic Conference
# ---------------------------------------------------------------------
USA_SOUTH_TEAMS = [
    Team(name="Brevard College", conference="USA_SOUTH", site_domain="bctornados.com"),
    Team(
        name="Greensboro College", conference="USA_SOUTH", site_domain="greensborocollegesports.com"
    ),
    Team(name="Methodist University", conference="USA_SOUTH", site_domain="mumonarchs.com"),
    Team(name="Pfeiffer University", conference="USA_SOUTH", site_domain="gofalconsports.com"),
    Team(name="William Peace University", conference="USA_SOUTH", site_domain="gopeacepacers.com"),
    Team(
        name="North Carolina Wesleyan University",
        conference="USA_SOUTH",
        site_domain="ncwsports.com",
    ),
    Team(
        name="Southern Virginia University",
        conference="USA_SOUTH",
        site_domain="knightathletics.com",
    ),
    Team(
        name="Mary Baldwin University",
        conference="USA_SOUTH",
        site_domain="marybaldwinathletics.com",
    ),
]
# Note: Meredith and Salem are women's colleges, no men's soccer -- excluded.

# ---------------------------------------------------------------------
# American Southwest Conference (ASC)
# ---------------------------------------------------------------------
ASC_TEAMS = [
    Team(name="East Texas Baptist University", conference="ASC", site_domain="goetbutigers.com"),
    Team(name="Hardin-Simmons University", conference="ASC", site_domain="hsuathletics.com"),
    Team(name="Howard Payne University", conference="ASC", site_domain="hpusports.com"),
    Team(name="University of Mary Hardin-Baylor", conference="ASC", site_domain="cruathletics.com"),
    Team(name="McMurry University", conference="ASC", site_domain="mcmurrysports.com"),
    Team(name="Schreiner University", conference="ASC", site_domain="schreinermountaineers.com"),
]
# Note: McMurry and Schreiner rejoin ASC for 2026-27 -- live standings page may lag and show
# only the prior 4 teams if pulled before conference play data posts. Schreiner's site
# returned 403 on automated fetches.

# ---------------------------------------------------------------------
# Coast-to-Coast Athletic Conference (C2C)
# ---------------------------------------------------------------------
C2C_TEAMS = [
    Team(name="Christopher Newport University", conference="C2C", site_domain="cnusports.com"),
    Team(
        name="Johnson & Wales University-Charlotte",
        conference="C2C",
        site_domain="charlotte.jwuathletics.com",
    ),
    Team(name="University of Mary Washington", conference="C2C", site_domain="umweagles.com"),
    Team(name="Regent University", conference="C2C", site_domain="regentroyals.com"),
    Team(name="Salisbury University", conference="C2C", site_domain="suseagulls.com"),
    Team(name="Warren Wilson College", conference="C2C", site_domain="warrenwilsonowls.com"),
]
# Note: C2C = "Coast-to-Coast Athletic Conference" (not "Continental"). c2csports.com and
# umweagles.com's msoc page both block automated fetches (403). Regent joined C2C in 2025-26.

# ---------------------------------------------------------------------
# Heartland Collegiate Athletic Conference (HCAC)
# ---------------------------------------------------------------------
HCAC_TEAMS = [
    Team(name="Anderson University", conference="HCAC", site_domain="athletics.anderson.edu"),
    Team(name="Berea College", conference="HCAC", site_domain="bereaathletics.com"),
    Team(name="Bluffton University", conference="HCAC", site_domain="blufftonbeavers.com"),
    Team(name="Earlham College", conference="HCAC", site_domain="goearlham.com"),
    Team(name="Franklin College", conference="HCAC", site_domain="franklingrizzlies.com"),
    Team(name="Hanover College", conference="HCAC", site_domain="athletics.hanover.edu"),
    Team(name="Manchester University", conference="HCAC", site_domain="muspartans.com"),
    Team(name="Mount St. Joseph University", conference="HCAC", site_domain="msjlions.com"),
    Team(
        name="Rose-Hulman Institute of Technology",
        conference="HCAC",
        site_domain="athletics.rose-hulman.edu",
    ),
    Team(
        name="Transylvania University",
        conference="HCAC",
        site_domain="transysports.com",
        sport_slug="msoc",
    ),
]
# Note: Anderson and Bluffton sites block automated fetches (403) on the mens-soccer subpage.
# Manchester leaves HCAC for NAIA after 2026-27 -- fine for this season.

# ---------------------------------------------------------------------
# Michigan Intercollegiate Athletic Association (MIAA)
# ---------------------------------------------------------------------
MIAA_TEAMS = [
    Team(name="Hope College", conference="MIAA", site_domain="athletics.hope.edu"),
    Team(name="University of Olivet", conference="MIAA", site_domain="olivetcomets.com"),
    Team(name="Calvin University", conference="MIAA", site_domain="calvinknights.com"),
    Team(name="Alma College", conference="MIAA", site_domain="almascots.com"),
    Team(name="Adrian College", conference="MIAA", site_domain="adrianbulldogs.com"),
    Team(name="Kalamazoo College", conference="MIAA", site_domain="hornets.kzoo.edu"),
    Team(name="Albion College", conference="MIAA", site_domain="gobrits.com"),
    Team(name="Trine University", conference="MIAA", site_domain="trinethunder.com"),
]
# Note: this is the Michigan Intercollegiate Athletic Association, not the East-Coast MIAA.
# Saint Mary's College (Notre Dame, IN) is a member but women's-only, no men's soccer -- excluded.

# ---------------------------------------------------------------------
# Northern Athletics Collegiate Conference (NACC)
# ---------------------------------------------------------------------
NACC_TEAMS = [
    Team(name="Aurora University", conference="NACC", site_domain="athletics.aurora.edu"),
    Team(name="Edgewood College", conference="NACC", site_domain="edgewoodeagles.com"),
    Team(name="Benedictine University", conference="NACC", site_domain="benueagles.com"),
    Team(name="Lakeland University", conference="NACC", site_domain="lakelandmuskies.com"),
    Team(name="St. Norbert College", conference="NACC", site_domain="athletics.snc.edu"),
    Team(name="Milwaukee School of Engineering", conference="NACC", site_domain="msoeraiders.com"),
    Team(
        name="Illinois Institute of Technology",
        conference="NACC",
        site_domain="illinoistechathletics.com",
    ),
    Team(name="Dominican University (IL)", conference="NACC", site_domain="dustars.com"),
    Team(name="Wisconsin Lutheran College", conference="NACC", site_domain="wlcsports.com"),
    Team(name="Concordia University Chicago", conference="NACC", site_domain="cucougars.com"),
    Team(name="Marian University (WI)", conference="NACC", site_domain="sabreathletics.com"),
]
# Note: 13-school NACC membership confirmed live. The 9 domains above (Benedictine through
# Marian WI) found via web search 2026-10-06, not independently fetched/verified -- spot-check
# on the next real pull. Marian (WI) here is Fond du Lac, not Marian University Indiana.
# Dominican here is the Illinois school (River Forest), not Dominican NY.
#
# Still missing: Rockford University (no dedicated athletics domain surfaced by search --
# may run under rockford.edu itself or a PrestoSports subdomain, needs manual confirmation).
#
# Concordia Wisconsin (cuwfalcons.com) was intentionally left OUT of the list above: search
# results turned up a "CUW to CCIW" item suggesting Concordia Wisconsin may have moved from
# NACC to CCIW for 2025-26, which would mean it's already in CCIW_TEAMS, not here -- this needs
# verifying before adding it to either list, to avoid double-counting or miscounting it.

# ---------------------------------------------------------------------
# College Conference of Illinois and Wisconsin (CCIW)
# ---------------------------------------------------------------------
CCIW_TEAMS = [
    Team(name="Augustana College", conference="CCIW", site_domain="athletics.augustana.edu"),
    Team(name="Carroll University", conference="CCIW", site_domain="gopios.com"),
    Team(name="Carthage College", conference="CCIW", site_domain="athletics.carthage.edu"),
    Team(name="Elmhurst University", conference="CCIW", site_domain="elmhurstbluejays.com"),
    Team(name="Illinois Wesleyan University", conference="CCIW", site_domain="www.iwusports.com"),
    Team(name="Millikin University", conference="CCIW", site_domain="athletics.millikin.edu"),
    Team(name="North Central College", conference="CCIW", site_domain="northcentralcardinals.com"),
    Team(name="North Park University", conference="CCIW", site_domain="athletics.northpark.edu"),
    Team(name="Wheaton College (IL)", conference="CCIW", site_domain="athletics.wheaton.edu"),
]
# Note: "North Central College" (CCIW, Naperville IL) != "North Central University" (UMAC,
# Minneapolis MN) -- do not dedupe these two.

# ---------------------------------------------------------------------
# Midwest Conference (MWC)
# ---------------------------------------------------------------------
MWC_TEAMS = [
    Team(name="Beloit College", conference="MWC", site_domain="beloitcollegeathletics.com"),
    Team(name="Cornell College", conference="MWC", site_domain="cornellrams.com"),
    Team(name="Grinnell College", conference="MWC", site_domain="pioneers.grinnell.edu"),
    Team(name="Illinois College", conference="MWC", site_domain="illinoiscollegeathletics.com"),
    Team(name="Knox College", conference="MWC", site_domain="prairiefire.knox.edu"),
    Team(name="Lake Forest College", conference="MWC", site_domain="goforesters.com"),
    Team(name="Lawrence University", conference="MWC", site_domain="vikings.lawrence.edu"),
    Team(name="Luther College", conference="MWC", site_domain="luthernorse.com"),
    Team(name="Monmouth College", conference="MWC", site_domain="monmouthscots.com"),
    Team(name="Ripon College", conference="MWC", site_domain="riponredhawks.com"),
]
# Note: Luther College moved here from the ARC starting 2026-27 -- don't put it in both.
# "Cornell College" (MWC, Iowa) != Cornell University.

# ---------------------------------------------------------------------
# American Rivers Conference (ARC)
# ---------------------------------------------------------------------
ARC_TEAMS = [
    Team(name="Buena Vista University", conference="ARC", site_domain="bvuathletics.com"),
    Team(name="Central College", conference="ARC", site_domain="athletics.central.edu"),
    Team(name="Coe College", conference="ARC", site_domain="kohawkathletics.com"),
    Team(name="University of Dubuque", conference="ARC", site_domain="udspartans.com"),
    Team(name="Loras College", conference="ARC", site_domain="duhawks.com"),
    Team(name="Nebraska Wesleyan University", conference="ARC", site_domain="nwusports.com"),
    Team(name="Wartburg College", conference="ARC", site_domain="go-knights.net"),
]
# Note: "A-R-C" = American Rivers Conference, not "Atlantic-Rio Grande" (doesn't exist).
# Luther College left for the MWC starting 2026-27 -- excluded here. Simpson College is an
# ARC member but runs PrestoSports, not Sidearm (simpson.prestosports.com) -- needs a
# separate scraper, not included in this Sidearm-based list.

# ---------------------------------------------------------------------
# St. Louis Intercollegiate Athletic Conference (SLIAC)
# ---------------------------------------------------------------------
SLIAC_TEAMS = [
    Team(
        name="Blackburn College",
        conference="SLIAC",
        site_domain="www.blackburnbeavers.com",
        sport_slug="msoc",
    ),
    Team(
        name="Eureka College",
        conference="SLIAC",
        site_domain="www.eurekareddevils.com",
        sport_slug="msoc",
    ),
    # athletics.greenville.edu now redirects to this domain's home page (probe, 2026-10-22).
    Team(name="Greenville University", conference="SLIAC", site_domain="greenvillepanthers.com"),
    Team(name="Lyon College", conference="SLIAC", site_domain="lyonscots.com"),
    Team(
        name="Mississippi University for Women", conference="SLIAC", site_domain="owlsathletics.com"
    ),
    Team(
        name="Principia College", conference="SLIAC", site_domain="athletics.principiacollege.edu"
    ),
    Team(name="Spalding University", conference="SLIAC", site_domain="spaldingathletics.com"),
    Team(name="Webster University", conference="SLIAC", site_domain="websterathletics.com"),
    Team(name="Westminster College (MO)", conference="SLIAC", site_domain="wcbluejays.wcmo.edu"),
]
# Note: Fontbonne closed after 2024-25 -- excluded. Blackburn/Eureka/Greenville sites have
# all shown 403s to automated fetches at various points -- may need special headers.

# ---------------------------------------------------------------------
# Upper Midwest Athletic Conference (UMAC)
# ---------------------------------------------------------------------
UMAC_TEAMS = [
    Team(name="Bethany Lutheran College", conference="UMAC", site_domain="blcvikings.com"),
    Team(name="Crown College", conference="UMAC", site_domain="athletics.crown.edu"),
    Team(name="Martin Luther College", conference="UMAC", site_domain="mlcknights.com"),
    Team(
        name="University of Minnesota, Morris", conference="UMAC", site_domain="morriscougars.com"
    ),
    Team(name="North Central University", conference="UMAC", site_domain="ncurams.com"),
    Team(
        name="University of Northwestern - St. Paul", conference="UMAC", site_domain="unweagles.com"
    ),
    Team(
        name="University of Wisconsin-Superior",
        conference="UMAC",
        site_domain="uwsyellowjackets.com",
    ),
]
# Note: "North Central University" (UMAC, Minneapolis MN) != "North Central College" (CCIW,
# Naperville IL) -- do not dedupe. St. Scholastica and Northland left UMAC previously
# (Northland ceased operations) -- excluded.


CONFERENCES = {
    "LEC": {"teams": LEC_TEAMS, "standings_url": "https://littleeast.com/standings.aspx?path=msoc"},
    "NAC": {
        "teams": NAC_TEAMS,
        "standings_url": "https://nacathletics.com/standings.aspx?path=msoc",
    },
    "MASCAC": {
        "teams": MASCAC_TEAMS,
        "standings_url": "https://www.mascac.com/standings.aspx?path=msoc",
    },
    "Skyline": {
        "teams": SKYLINE_TEAMS,
        "standings_url": "https://skylineconference.org/standings.aspx?path=msoc",
    },
    "SUNYAC": {
        "teams": SUNYAC_TEAMS,
        "standings_url": "https://sunyacsports.com/standings.aspx?path=msoc",
    },
    "GNAC": {
        "teams": GNAC_TEAMS,
        "standings_url": "https://www.thegnac.com/standings.aspx?path=msoc",
    },
    "CUNYAC": {
        "teams": CUNYAC_TEAMS,
        "standings_url": "https://cunyathletics.com/standings.aspx?path=msoccer",
    },
    "UNITED_EAST": {
        "teams": UNITED_EAST_TEAMS,
        "standings_url": "https://gounitedeast.com/standings.aspx?path=msoc",
    },
    "ATLANTIC_EAST": {
        "teams": ATLANTIC_EAST_TEAMS,
        "standings_url": "https://atlanticeast.com/standings.aspx?path=msoc",
    },
    "MAC_COMMONWEALTH": {
        "teams": MAC_COMMONWEALTH_TEAMS,
        "standings_url": "https://gomacsports.com/standings.aspx?path=msoc&div=mac-commonwealth",
    },
    "MAC_FREEDOM": {
        "teams": MAC_FREEDOM_TEAMS,
        "standings_url": "https://gomacsports.com/standings.aspx?path=msoc&div=mac-freedom",
    },
    "LANDMARK": {
        "teams": LANDMARK_TEAMS,
        "standings_url": "https://landmarkconference.org/standings.aspx?path=msoc",
    },
    "AMCC": {
        "teams": AMCC_TEAMS,
        "standings_url": "https://www.amccsports.org/standings.aspx?path=msoc",
    },
    "PAC": {
        "teams": PAC_TEAMS,
        "standings_url": "https://pacathletics.org/standings.aspx?path=msoc",
    },
    "ODAC": {
        "teams": ODAC_TEAMS,
        "standings_url": "https://odaconline.com/standings.aspx?path=msoc",
    },
    "SAA": {"teams": SAA_TEAMS, "standings_url": "https://saa-sports.com/standings.aspx?path=msoc"},
    "SCAC": {
        "teams": SCAC_TEAMS,
        "standings_url": "https://scacsports.com/standings.aspx?path=msoc",
    },
    "USA_SOUTH": {
        "teams": USA_SOUTH_TEAMS,
        "standings_url": "https://usasouth.net/standings.aspx?path=msoc",
    },
    "ASC": {"teams": ASC_TEAMS, "standings_url": "https://ascsports.org/standings.aspx?path=msoc"},
    "C2C": {
        "teams": C2C_TEAMS,
        "standings_url": "https://www.c2csports.com/sports/msoc/2025-26/standings",
    },
    "HCAC": {
        "teams": HCAC_TEAMS,
        "standings_url": "https://heartlandconf.org/standings.aspx?path=msoc",
    },
    "MIAA": {"teams": MIAA_TEAMS, "standings_url": "https://miaa.org/standings.aspx?path=msoc"},
    "NACC": {
        "teams": NACC_TEAMS,
        "standings_url": "https://naccsports.org/standings.aspx?path=msoc",
    },
    "CCIW": {"teams": CCIW_TEAMS, "standings_url": "https://cciw.org/standings.aspx?path=msoc"},
    "MWC": {
        "teams": MWC_TEAMS,
        "standings_url": "https://midwestconference.org/standings.aspx?path=msoc",
    },
    "ARC": {"teams": ARC_TEAMS, "standings_url": "https://rollrivers.com/standings.aspx?path=msoc"},
    "SLIAC": {"teams": SLIAC_TEAMS, "standings_url": "https://sliac.org/standings.aspx?path=msoc"},
    "UMAC": {
        "teams": UMAC_TEAMS,
        "standings_url": "https://umacathletics.com/standings.aspx?path=msoc",
    },
    "NESCAC": {"teams": NESCAC_TEAMS, "standings_url": None},  # see fetch_nescac_standings
    "UAA": {"teams": UAA_TEAMS, "standings_url": "https://uaasports.info/standings.aspx?path=msoc"},
    "MIAC": {
        "teams": MIAC_TEAMS,
        "standings_url": "https://miacathletics.com/standings.aspx?path=msoc",
    },
    "WIAC": {
        "teams": WIAC_TEAMS,
        "standings_url": "https://wiacsports.com/standings.aspx?path=msoc",
    },
    "Northwest Conference": {
        "teams": NWC_TEAMS,
        "standings_url": "https://nwcsports.com/standings.aspx?path=msoc",
    },
    "Liberty League": {
        "teams": LIBERTY_LEAGUE_TEAMS,
        "standings_url": "https://libertyleagueathletics.com/standings.aspx?path=msoc",
    },
    "Centennial": {
        "teams": CENTENNIAL_TEAMS,
        "standings_url": "https://centennial.org/standings.aspx?path=msoc",
    },
    "Empire 8": {
        "teams": EMPIRE8_TEAMS,
        "standings_url": "https://empire8.com/standings.aspx?path=msoc",
    },
    "OAC": {"teams": OAC_TEAMS, "standings_url": "https://oac.org/standings.aspx?path=msoc"},
    "NCAC": {
        "teams": NCAC_TEAMS,
        "standings_url": "https://northcoast.org/standings.aspx?path=msoc",
    },
    "NJAC": {
        "teams": NJAC_TEAMS,
        "standings_url": "https://njacsports.com/standings.aspx?path=msoc",
    },
    "NEWMAC": {
        "teams": NEWMAC_TEAMS,
        "standings_url": "https://newmacsports.com/standings.aspx?path=msoc",
    },
}


def _norm(header: str) -> str:
    return " ".join(header.split()).lower()


def _first_matching(row_map: dict, *candidates: str) -> str | None:
    """Case- and whitespace-insensitive lookup trying several possible header spellings."""
    lower_map = {_norm(k): v for k, v in row_map.items()}
    for c in candidates:
        if _norm(c) in lower_map:
            return lower_map[_norm(c)]
    return None


def _conf_record_fallback(row_map: dict) -> str | None:
    """A "<Conference> Record" column, e.g. Atlantic East's "AEC Record"."""
    for header, value in row_map.items():
        h = _norm(header)
        if h.endswith("record") and "overall" not in h:
            return value
    return None


def _parse_sidearm_standings_table(html: str, conference_name: str) -> list[StandingRow]:
    """
    Shared parser for the `table.sidearm-standings-table` layout confirmed
    live against SCIAC, UAA, MIAC, WIAC, NWC, and NESCAC. The table itself
    and its responsive hide-on-medium-down/hide-on-large column-doubling
    are consistent across all of them, but the actual header TEXT varies
    per conference site -- SCIAC/UAA/WIAC/NWC use "School"/"CONF. W-L"/
    "W-L"/"CONF. PCT", while MIAC (and apparently NESCAC, same template
    family) use "TEAM"/"Conf"/"Overall"/"CPct." instead. Confirmed via
    real raw HTML from miacathletics.com on 2026-09-18 -- the original
    version of this parser silently returned 0 rows for MIAC/NESCAC
    because it only looked for the SCIAC-style header names. This version
    tries several known spellings per field instead of hardcoding one.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.sidearm-standings-table")
    if not table:
        return []

    thead = table.find("thead")
    raw_headers = [
        th.get_text(strip=True)
        for th in thead.select("th.hide-on-medium-down, th:not(.hide-on-large)")
    ]
    headers: list[str] = []
    for h in raw_headers:
        if not headers or headers[-1] != h:
            headers.append(h)
    # Keep repeated names distinct ("Win %" for conference, then "Win % #2" for overall)
    # so the first one isn't overwritten when zipped into a dict.
    seen: dict[str, int] = {}
    for i, h in enumerate(headers):
        seen[h] = seen.get(h, 0) + 1
        if seen[h] > 1:
            headers[i] = f"{h} #{seen[h]}"

    rows: list[StandingRow] = []
    for tr in table.select("tbody tr"):
        cells = tr.select("td.hide-on-medium-down")
        vals = [c.get_text(strip=True) for c in cells]
        if len(vals) < 2:
            continue
        row_map = dict(zip(headers, vals))
        # Team column names seen: School, Team, Institution (NAC), Schools (Atlantic
        # East), "School Name With Logo (link to Schedule)" (SLIAC). It is always first.
        team_name = _first_matching(row_map, "School", "Team", "Institution", "Schools") or vals[0]
        if not team_name:
            continue
        rows.append(
            StandingRow(
                conference=conference_name,
                team=team_name,
                conf_record=_first_matching(row_map, "CONF. W-L", "Conf", "Conference", "C-REC")
                or _conf_record_fallback(row_map)
                or "",
                overall_record=_first_matching(row_map, "W-L", "Overall", "O-REC", "Overall Record")
                or "",
                conf_points=_first_matching(row_map, "CONF. PCT", "CPct.", "C-W%", "Win %", "Pct."),
            )
        )
    return rows


def fetch_standings(conference_key: str) -> list[StandingRow]:
    """Fetch current standings for any conference in CONFERENCES except NESCAC."""
    cfg = CONFERENCES[conference_key]
    if cfg["standings_url"] is None:
        raise ValueError(
            f"{conference_key} has no static standings URL -- use its dedicated fetch function"
        )
    resp = requests.get(cfg["standings_url"], headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return _parse_sidearm_standings_table(resp.text, conference_key)


def fetch_nescac_standings() -> list[StandingRow]:
    """
    NESCAC has no season-agnostic standings URL. This tries to resolve the
    current season's numeric standings id from the sport hub page
    (nescac.com/sports/msoc) by regex-matching a `standings=<id>` link,
    falling back to NESCAC_FALLBACK_STANDINGS_ID if that lookup ever
    breaks (e.g. NESCAC changes their page template).
    """
    standings_id = NESCAC_FALLBACK_STANDINGS_ID
    try:
        hub_resp = requests.get("https://nescac.com/sports/msoc", headers=HEADERS, timeout=TIMEOUT)
        hub_resp.raise_for_status()
        match = re.search(r"standings\.aspx\?standings=(\d+)", hub_resp.text)
        if match:
            standings_id = int(match.group(1))
    except requests.RequestException:
        pass  # fall back to the hardcoded id

    url = f"https://nescac.com/standings.aspx?standings={standings_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return _parse_sidearm_standings_table(resp.text, "NESCAC")
