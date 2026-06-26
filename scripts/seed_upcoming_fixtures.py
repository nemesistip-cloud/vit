import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Match

FIXTURES = [
  {
    "time": "26 Jun, 12:30",
    "league": "Australia – Western Australia Division 1, W...",
    "home_team": "Perth AFC",
    "away_team": "Murdoch Univers...",
    "odds_home": 1.66,
    "odds_draw": 3.80,
    "odds_away": 4.25
  },
  {
    "time": "26 Jun, 12:35",
    "league": "China – Chinese Super League",
    "home_team": "Qingdao Hainiu FC",
    "away_team": "Yunnan Yukun",
    "odds_home": 2.85,
    "odds_draw": 3.75,
    "odds_away": 2.30
  },
  {
    "time": "26 Jun, 13:00",
    "league": "International Clubs – Club Friendly Games",
    "home_team": "Malmo",
    "away_team": "FC Midtjylland",
    "odds_home": 3.10,
    "odds_draw": 3.60,
    "odds_away": 2.00
  },
  {
    "time": "26 Jun, 13:00",
    "league": "Russia – MFL, Division A",
    "home_team": "Football Academ...",
    "away_team": "Chertanovo Mos...",
    "odds_home": 1.99,
    "odds_draw": 3.90,
    "odds_away": 2.70
  },
  {
    "time": "26 Jun, 13:00",
    "league": "Russia – MFL, Division A",
    "home_team": "Rubin Kazan",
    "away_team": "Lokomotiv Moscow",
    "odds_home": 10.00,
    "odds_draw": 5.90,
    "odds_away": 1.16
  },
  {
    "time": "26 Jun, 13:00",
    "league": "Ethiopia – Premier League",
    "home_team": "Saint George SC",
    "away_team": "Fasil Kenema SC",
    "odds_home": 2.25,
    "odds_draw": 2.65,
    "odds_away": 3.60
  },
  {
    "time": "26 Jun, 13:00",
    "league": "Kazakhstan - Pervaya Liga",
    "home_team": "FK Ekibastuz",
    "away_team": "FC Astana Reserve",
    "odds_home": 2.25,
    "odds_draw": 3.60,
    "odds_away": 2.70
  },
  {
    "time": "26 Jun, 13:45",
    "league": "Mozambique - Mocambola",
    "home_team": "Ferroviaro de Li...",
    "away_team": "Costa Do Sol",
    "odds_home": 2.35,
    "odds_draw": 2.65,
    "odds_away": 3.10
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Georgia - Cup",
    "home_team": "FC Guria Lanchk...",
    "away_team": "FC Merani Tbilisi",
    "odds_home": 1.59,
    "odds_draw": 4.20,
    "odds_away": 4.30
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Georgia - Cup",
    "home_team": "Gardabani",
    "away_team": "FC Iberia 2010 T...",
    "odds_home": 1.70,
    "odds_draw": 3.90,
    "odds_away": 3.90
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Ethiopia - Premier League",
    "home_team": "Ethiopian Coffee ...",
    "away_team": "Mekelle 70 Ender...",
    "odds_home": 3.00,
    "odds_draw": 2.80,
    "odds_away": 2.45
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Zimbabwe - Premier Soccer League",
    "home_team": "Scottland FC",
    "away_team": "Manica Diamond...",
    "odds_home": 1.33,
    "odds_draw": 4.10,
    "odds_away": 9.40
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Kazakhstan - Pervaya Liga",
    "home_team": "FC Taraz",
    "away_team": "Shakhtar Karaga...",
    "odds_home": 8.90,
    "odds_draw": 5.90,
    "odds_away": 1.22
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "EC Agua Santa SP",
    "away_team": "AA Flamengo SP",
    "odds_home": 1.49,
    "odds_draw": 4.10,
    "odds_away": 5.40
  },
  {
    "time": "26 Jun, 14:00",
    "league": "Sweden Amateur - U19 Allsvenskan",
    "home_team": "Kalmar FF",
    "away_team": "Västeras SK FK ...",
    "odds_home": 2.80,
    "odds_draw": 3.40,
    "odds_away": 2.10
  },
  {
    "time": "26 Jun, 14:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FK Jablonec",
    "away_team": "FC Vlasim",
    "odds_home": 1.53,
    "odds_draw": 4.20,
    "odds_away": 4.80
  },
  {
    "time": "26 Jun, 15:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FK Rubin Kazan",
    "away_team": "FC Kamaz Naber...",
    "odds_home": 1.50,
    "odds_draw": 4.20,
    "odds_away": 5.10
  },
  {
    "time": "26 Jun, 15:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SV Ried",
    "away_team": "Austria Salzburg",
    "odds_home": 1.39,
    "odds_draw": 4.90,
    "odds_away": 5.75
  },
  {
    "time": "26 Jun, 15:00",
    "league": "Russia - MFL, Division A",
    "home_team": "FK Rostov",
    "away_team": "FC Fakel Voronez...",
    "odds_home": 1.33,
    "odds_draw": 4.60,
    "odds_away": 6.30
  },
  {
    "time": "26 Jun, 15:00",
    "league": "Russia - MFL, Division A",
    "home_team": "FK Zenit St. Pete...",
    "away_team": "FK Nizhny Novgor...",
    "odds_home": 1.03,
    "odds_draw": 8.20,
    "odds_away": 25.0
  },
  {
    "time": "26 Jun, 16:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "IK Sirius",
    "away_team": "Djurgardens IF",
    "odds_home": 2.15,
    "odds_draw": 3.60,
    "odds_away": 2.65
  },
  {
    "time": "26 Jun, 16:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "MTK Budapest",
    "away_team": "Kazincbarcikai SC",
    "odds_home": 1.53,
    "odds_draw": 4.00,
    "odds_away": 4.80
  },
  {
    "time": "26 Jun, 16:00",
    "league": "Russia - MFL, Division A",
    "home_team": "FC Rodina Youth",
    "away_team": "CSKA Moscow",
    "odds_home": 5.30,
    "odds_draw": 4.50,
    "odds_away": 1.40
  },
  {
    "time": "26 Jun, 16:00",
    "league": "Latvia - Virslīga",
    "home_team": "Ogre United",
    "away_team": "FK Tukums 2000...",
    "odds_home": 3.80,
    "odds_draw": 3.60,
    "odds_away": 1.85
  },
  {
    "time": "26 Jun, 16:00",
    "league": "Belarus - Vysshaya Liga",
    "home_team": "FC Baranovichi",
    "away_team": "FC Slavia Mozyr",
    "odds_home": 3.10,
    "odds_draw": 3.30,
    "odds_away": 2.25
  },
  {
    "time": "26 Jun, 16:00",
    "league": "Ethiopia - Premier League",
    "home_team": "Arba Minch Kete...",
    "away_team": "Welwalo Adigrat",
    "odds_home": 6.90,
    "odds_draw": 3.40,
    "odds_away": 1.51
  },
  {
    "time": "26 Jun, 16:30",
    "league": "Lithuania - 1 Lyga",
    "home_team": "Be1 Nfa",
    "away_team": "Vilnius FK Zalgiri...",
    "odds_home": 1.40,
    "odds_draw": 4.40,
    "odds_away": 6.40
  },
  {
    "time": "26 Jun, 16:30",
    "league": "Finland - Kakkonen",
    "home_team": "Abo IFK Turku",
    "away_team": "FC Honka",
    "odds_home": 4.10,
    "odds_draw": 4.10,
    "odds_away": 1.69
  },
  {
    "time": "26 Jun, 16:45",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Dukla Prague",
    "away_team": "FK Mlada Boleslav",
    "odds_home": 2.75,
    "odds_draw": 3.80,
    "odds_away": 2.05
  },
  {
    "time": "26 Jun, 17:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Rapperswil-J...",
    "away_team": "Basel",
    "odds_home": 5.80,
    "odds_draw": 4.80,
    "odds_away": 1.73
  },
  {
    "time": "26 Jun, 17:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SC/ESV Parndorf...",
    "away_team": "FK Austria Wien",
    "odds_home": 15.00,
    "odds_draw": 7.00,
    "odds_away": 1.11
  },
  {
    "time": "26 Jun, 17:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SV Horn",
    "away_team": "SKN St Polten",
    "odds_home": 5.20,
    "odds_draw": 4.70,
    "odds_away": 1.42
  },
  {
    "time": "26 Jun, 17:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SV Seekirchen",
    "away_team": "Salzburg",
    "odds_home": 24.00,
    "odds_draw": 12.50,
    "odds_away": 1.01
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Russia - MFL, Division A",
    "home_team": "FC Krasnodar",
    "away_team": "Dinamo Moscow",
    "odds_home": 1.49,
    "odds_draw": 4.25,
    "odds_away": 4.40
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Latvia - Virslīga",
    "home_team": "FK Liepaja",
    "away_team": "FK Rīgas Futbola ...",
    "odds_home": 6.70,
    "odds_draw": 4.75,
    "odds_away": 1.30
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Finland - Ykkosliiga",
    "home_team": "HJK Klubi 04",
    "away_team": "SJK Akatemia",
    "odds_home": 2.05,
    "odds_draw": 3.50,
    "odds_away": 3.33
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Finland - Ykkosliiga",
    "home_team": "PK-35 Helsinki",
    "away_team": "Mikkelin Palloilijat",
    "odds_home": 1.74,
    "odds_draw": 3.60,
    "odds_away": 4.70
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Norway - 2nd Division Group 2",
    "home_team": "Eidsvold TF",
    "away_team": "Tromsdalen UIL",
    "odds_home": 1.64,
    "odds_draw": 4.20,
    "odds_away": 4.25
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Norway - 3. Division, Group 1",
    "home_team": "Valerenga IF 2",
    "away_team": "FK Union Carl Be...",
    "odds_home": 3.25,
    "odds_draw": 4.20,
    "odds_away": 1.81
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Norway - 3. Division, Group 4",
    "home_team": "Flekkeroy IL",
    "away_team": "Akra",
    "odds_home": 1.14,
    "odds_draw": 7.25,
    "odds_away": 11.50
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Norway - 3. Division, Group 5",
    "home_team": "Skedsmo",
    "away_team": "Skjetten",
    "odds_home": 1.62,
    "odds_draw": 4.40,
    "odds_away": 3.90
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Argentina - Primera Division, Women",
    "home_team": "CA River Plate (A...)",
    "away_team": "Newell's Old Boys",
    "odds_home": 1.35,
    "odds_draw": 4.25,
    "odds_away": 8.10
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Finland - Kolmonen",
    "home_team": "Komeetat",
    "away_team": "Savon Pallo",
    "odds_home": 2.80,
    "odds_draw": 4.10,
    "odds_away": 2.00
  },
  {
    "time": "26 Jun, 17:00",
    "league": "Finland - Kolmonen",
    "home_team": "LTU",
    "away_team": "Vg-62",
    "odds_home": 2.60,
    "odds_draw": 3.80,
    "odds_away": 2.20
  },
  {
    "time": "26 Jun, 17:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "KAC 1909",
    "away_team": "Atus Velden",
    "odds_home": 9.20,
    "odds_draw": 6.20,
    "odds_away": 1.10
  },
  {
    "time": "26 Jun, 17:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Mattersburger S...",
    "away_team": "Kapfenberger SV",
    "odds_home": 5.90,
    "odds_draw": 5.25,
    "odds_away": 1.33
  },
  {
    "time": "26 Jun, 17:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "NK Radomlje",
    "away_team": "GNK Dinamo Zag...",
    "odds_home": 9.25,
    "odds_draw": 5.80,
    "odds_away": 1.21
  },
  {
    "time": "26 Jun, 17:30",
    "league": "Lithuania - 1 Lyga",
    "home_team": "FK Gartlava",
    "away_team": "FK Minija 2017",
    "odds_home": 4.60,
    "odds_draw": 3.70,
    "odds_away": 1.63
  },
  {
    "time": "26 Jun, 17:30",
    "league": "Lithuania - II Lyga",
    "home_team": "FKS Ukmerge",
    "away_team": "FK Silute",
    "odds_home": 1.56,
    "odds_draw": 4.30,
    "odds_away": 4.40
  },
  {
    "time": "26 Jun, 17:30",
    "league": "Lithuania - II Lyga",
    "home_team": "Vilnius Football ...",
    "away_team": "Kedainiai Nevezis",
    "odds_home": 2.15,
    "odds_draw": 3.75,
    "odds_away": 2.70
  },
  {
    "time": "26 Jun, 17:30",
    "league": "Finland - Kolmonen",
    "home_team": "Valtti",
    "away_team": "MPS/Atletico Mal...",
    "odds_home": 2.25,
    "odds_draw": 4.00,
    "odds_away": 2.45
  },
  {
    "time": "26 Jun, 18:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SC Weiz",
    "away_team": "FC Marchfeld Do...",
    "odds_home": 2.85,
    "odds_draw": 3.90,
    "odds_away": 1.99
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Superettan",
    "home_team": "IK Brage",
    "away_team": "Falkenbergs FF",
    "odds_home": 2.45,
    "odds_draw": 3.60,
    "odds_away": 2.70
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Ettan",
    "home_team": "FBK Karlstad",
    "away_team": "Hammarby Talan...",
    "odds_home": 3.60,
    "odds_draw": 3.80,
    "odds_away": 1.85
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Ettan",
    "home_team": "Kristianstad FC",
    "away_team": "Trelleborgs FF",
    "odds_home": 4.50,
    "odds_draw": 3.90,
    "odds_away": 1.67
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Ettan",
    "home_team": "Sollentuna FK",
    "away_team": "AFC Eskilstuna",
    "odds_home": 2.25,
    "odds_draw": 3.60,
    "odds_away": 2.80
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Estonia - Premium Liiga",
    "home_team": "Parnu JK Vaprus",
    "away_team": "FC Kuressaare",
    "odds_home": 1.95,
    "odds_draw": 3.60,
    "odds_away": 3.40
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Division 2",
    "home_team": "Kungsangens IF",
    "away_team": "Skiljebo SK",
    "odds_home": 2.85,
    "odds_draw": 3.50,
    "odds_away": 2.15
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Sweden - Division 2",
    "home_team": "Onsala BK",
    "away_team": "Landvetter IS",
    "odds_home": 2.90,
    "odds_draw": 3.40,
    "odds_away": 2.15
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Belarus - Vysshaya Liga",
    "home_team": "FK Arsenal Dzerz...",
    "away_team": "FC Gomel",
    "odds_home": 4.00,
    "odds_draw": 3.33,
    "odds_away": 1.92
  },
  {
    "time": "26 Jun, 18:00",
    "league": "Chile - Segunda Division",
    "home_team": "Santiago City FC",
    "away_team": "CD Provincial Ov...",
    "odds_home": 1.70,
    "odds_draw": 3.60,
    "odds_away": 4.30
  },
  {
    "time": "26 Jun, 18:15",
    "league": "Sweden - Division 2",
    "home_team": "Vänersborgs IF",
    "away_team": "Stenungsunds IF",
    "odds_home": 3.25,
    "odds_draw": 3.90,
    "odds_away": 1.87
  },
  {
    "time": "26 Jun, 18:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Zaglebie Lubin",
    "away_team": "Miedz Legnica",
    "odds_home": 1.71,
    "odds_draw": 3.70,
    "odds_away": 3.90
  },
  {
    "time": "26 Jun, 18:30",
    "league": "Sweden - Ettan",
    "home_team": "Assyriska FF",
    "away_team": "Vasalunds IF",
    "odds_home": 2.95,
    "odds_draw": 3.60,
    "odds_away": 2.15
  },
  {
    "time": "26 Jun, 18:30",
    "league": "Sweden - Ettan",
    "home_team": "Hassleholms IF",
    "away_team": "Tvaakers IF",
    "odds_home": 1.97,
    "odds_draw": 3.60,
    "odds_away": 3.40
  },
  {
    "time": "26 Jun, 18:30",
    "league": "Sweden - Division 2",
    "home_team": "Dalstorps IF",
    "away_team": "Lindome GIF",
    "odds_home": 2.00,
    "odds_draw": 3.60,
    "odds_away": 3.00
  },
  {
    "time": "26 Jun, 18:30",
    "league": "Sweden - Division 2",
    "home_team": "IFK Berga",
    "away_team": "Vaxjo Norra",
    "odds_home": 2.55,
    "odds_draw": 3.50,
    "odds_away": 2.40
  },
  {
    "time": "26 Jun, 18:30",
    "league": "Sweden - Division 2",
    "home_team": "Skara FC",
    "away_team": "Herrestads AIF",
    "odds_home": 1.59,
    "odds_draw": 3.90,
    "odds_away": 4.70
  },
  {
    "time": "26 Jun, 18:45",
    "league": "Kuwait - Premier League",
    "home_team": "AL Tadhamon",
    "away_team": "Al Shabab Kuwait",
    "odds_home": 2.65,
    "odds_draw": 3.20,
    "odds_away": 2.45
  },
  {
    "time": "26 Jun, 18:45",
    "league": "Kuwait - Premier League",
    "home_team": "Al-Nasr SC",
    "away_team": "Al Jahra",
    "odds_home": 1.44,
    "odds_draw": 4.00,
    "odds_away": 6.50
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "AE Velo Clube SP",
    "away_team": "SC Aguai SP U20",
    "odds_home": 1.74,
    "odds_draw": 3.50,
    "odds_away": 4.20
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "Botafogo FC SP",
    "away_team": "EC XV de Novem...",
    "odds_home": 1.78,
    "odds_draw": 3.60,
    "odds_away": 3.80
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "CA Bandeirante SP",
    "away_team": "Oeste FC SP",
    "odds_home": 3.80,
    "odds_draw": 3.60,
    "odds_away": 1.77
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "CA Juventus SP",
    "away_team": "Uniao Suzano AC ...",
    "odds_home": 1.65,
    "odds_draw": 3.50,
    "odds_away": 4.70
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "EC Sao Bernardo ...",
    "away_team": "EC Santo Andre SP",
    "odds_home": 1.53,
    "odds_draw": 3.80,
    "odds_away": 5.40
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "Gremio Osasco A...",
    "away_team": "Porto Foot Ball SP",
    "odds_home": 1.40,
    "odds_draw": 4.50,
    "odds_away": 6.20
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "Mirassol FC SP",
    "away_team": "Jabaquara AC SP",
    "odds_home": 1.46,
    "odds_draw": 4.20,
    "odds_away": 5.70
  },
  {
    "time": "26 Jun, 19:00",
    "league": "Brazil - U20 Paulista",
    "home_team": "Referencia FC SP",
    "away_team": "Gd Prudente SP ...",
    "odds_home": 2.85,
    "odds_draw": 3.20,
    "odds_away": 2.30
  },
  {
    "time": "26 Jun, 20:15",
    "league": "Iceland - 2. deild",
    "home_team": "UMF Selfoss",
    "away_team": "Haukar Hafnarfjo...",
    "odds_home": 2.65,
    "odds_draw": 3.90,
    "odds_away": 2.15
  },
  {
    "time": "26 Jun, 20:15",
    "league": "Iceland - 3. deild",
    "home_team": "Augnablik Kopav...",
    "away_team": "KH Hlidarendi",
    "odds_home": 3.40,
    "odds_draw": 4.20,
    "odds_away": 1.75
  },
  {
    "time": "26 Jun, 20:15",
    "league": "Iceland - 3. deild",
    "home_team": "KV Vesturbær",
    "away_team": "UMF Vidir",
    "odds_home": 4.80,
    "odds_draw": 5.10,
    "odds_away": 1.44
  },
  {
    "time": "26 Jun, 21:15",
    "league": "Peru - Copa de la Liga",
    "home_team": "CSDC Alianza Uni...",
    "away_team": "Union Minas",
    "odds_home": 1.57,
    "odds_draw": 3.75,
    "odds_away": 5.10
  },
  {
    "time": "26 Jun, 21:15",
    "league": "Peru - Copa de la Liga",
    "home_team": "Sport Huancayo",
    "away_team": "Asociacion Depo...",
    "odds_home": 2.20,
    "odds_draw": 3.10,
    "odds_away": 3.00
  },
  {
    "time": "26 Jun, 22:30",
    "league": "Canada - Canadian Premier League",
    "home_team": "HFX Wanderers FC",
    "away_team": "Pacific FC",
    "odds_home": 1.90,
    "odds_draw": 3.50,
    "odds_away": 3.70
  },
  {
    "time": "26 Jun, 23:00",
    "league": "Brazil - Brasileiro Serie B",
    "home_team": "Gremio Novorizó...",
    "away_team": "Vila Nova FC GO",
    "odds_home": 2.10,
    "odds_draw": 3.20,
    "odds_away": 3.75
  },
  {
    "time": "26 Jun, 23:00",
    "league": "New Zealand - National League",
    "home_team": "Selwyn United FC",
    "away_team": "Coastal Spirit FC",
    "odds_home": 6.90,
    "odds_draw": 5.40,
    "odds_away": 1.25
  },
  {
    "time": "27 Jun, 00:00",
    "league": "Chile - Copa Chile",
    "home_team": "CD Everton Vina",
    "away_team": "Deportes Copiapo",
    "odds_home": 1.70,
    "odds_draw": 3.80,
    "odds_away": 4.30
  },
  {
    "time": "27 Jun, 00:00",
    "league": "USA - MLS Next Pro",
    "home_team": "Connecticut United",
    "away_team": "New York City F...",
    "odds_home": 1.40,
    "odds_draw": 4.90,
    "odds_away": 6.30
  },
  {
    "time": "27 Jun, 00:30",
    "league": "USA - USL League Two",
    "home_team": "Western Mass Pi...",
    "away_team": "AC Connecticut",
    "odds_home": 1.19,
    "odds_draw": 6.60,
    "odds_away": 9.30
  },
  {
    "time": "27 Jun, 01:00",
    "league": "International - World Cup",
    "home_team": "Cape Verde",
    "away_team": "Saudi Arabia",
    "odds_home": 2.70,
    "odds_draw": 3.40,
    "odds_away": 2.82
  },
  {
    "time": "27 Jun, 01:00",
    "league": "International - World Cup",
    "home_team": "Uruguay",
    "away_team": "Spain",
    "odds_home": 6.20,
    "odds_draw": 4.00,
    "odds_away": 1.64
  },
  {
    "time": "27 Jun, 01:00",
    "league": "New Zealand - National League",
    "home_team": "Auckland City FC",
    "away_team": "Western Springs ...",
    "odds_home": 1.62,
    "odds_draw": 3.75,
    "odds_away": 4.00
  },
  {
    "time": "27 Jun, 01:00",
    "league": "New Zealand - National League",
    "home_team": "East Coast Bays",
    "away_team": "Tauranga City AFC",
    "odds_home": 1.67,
    "odds_draw": 3.80,
    "odds_away": 3.70
  },
  {
    "time": "27 Jun, 02:00",
    "league": "USA - USL League Two",
    "home_team": "Snohomish United",
    "away_team": "Bigfoot FC",
    "odds_home": 1.04,
    "odds_draw": 11.00,
    "odds_away": 22.00
  },
  {
    "time": "27 Jun, 02:00",
    "league": "New Zealand - National League",
    "home_team": "Bay Olympic",
    "away_team": "Fencibles United ...",
    "odds_home": 5.70,
    "odds_draw": 4.40,
    "odds_away": 1.38
  },
  {
    "time": "27 Jun, 02:00",
    "league": "New Zealand - National League",
    "home_team": "Petone FC",
    "away_team": "Wellington Phone ...",
    "odds_home": 3.10,
    "odds_draw": 4.00,
    "odds_away": 1.89
  },
  {
    "time": "27 Jun, 02:45",
    "league": "Australia - South Australia NPL, Reserves ...",
    "home_team": "Adelaide Comets ...",
    "away_team": "West Torrens Bir ...",
    "odds_home": 1.10,
    "odds_draw": 7.10,
    "odds_away": 12.50
  },
  {
    "time": "27 Jun, 03:00",
    "league": "USA - USL League Two",
    "home_team": "FC Tucson",
    "away_team": "City SC San Diego",
    "odds_home": 1.57,
    "odds_draw": 4.20,
    "odds_away": 4.47
  },
  {
    "time": "27 Jun, 03:00",
    "league": "New Zealand - National League",
    "home_team": "Wanaka AFC",
    "away_team": "Northern AFC",
    "odds_home": 4.60,
    "odds_draw": 4.10,
    "odds_away": 1.50
  },
  {
    "time": "27 Jun, 03:00",
    "league": "Australia - Northern NSW NPL, Reserves",
    "home_team": "Charlestown Azz...",
    "away_team": "Belmont Swanse...",
    "odds_home": 1.22,
    "odds_draw": 6.00,
    "odds_away": 8.70
  },
  {
    "time": "27 Jun, 03:00",
    "league": "Australia - Northern NSW NPL, Reserves",
    "home_team": "Edgeworth FC Re...",
    "away_team": "Adamstown Rose...",
    "odds_home": 1.91,
    "odds_draw": 4.00,
    "odds_away": 3.10
  },
  {
    "time": "27 Jun, 03:00",
    "league": "Australia - Northern NSW NPL, Reserves",
    "home_team": "Newcastle Olym...",
    "away_team": "Cooks Hill United...",
    "odds_home": 2.10,
    "odds_draw": 3.80,
    "odds_away": 2.80
  },
  {
    "time": "27 Jun, 03:00",
    "league": "Australia - South Australia State League 1...",
    "home_team": "Eastern United R...",
    "away_team": "Cumberland Unit...",
    "odds_home": 3.10,
    "odds_draw": 4.40,
    "odds_away": 1.87
  },
  {
    "time": "27 Jun, 03:30",
    "league": "Australia - U23 Queensland NPL",
    "home_team": "Magic United TFA",
    "away_team": "Brisbane City",
    "odds_home": 4.60,
    "odds_draw": 4.75,
    "odds_away": 1.42
  },
  {
    "time": "27 Jun, 03:45",
    "league": "New Zealand - National League",
    "home_team": "Cashmere Techni...",
    "away_team": "Ferrymead Bays",
    "odds_home": 1.24,
    "odds_draw": 5.25,
    "odds_away": 7.60
  },
  {
    "time": "27 Jun, 03:45",
    "league": "New Zealand - National League",
    "home_team": "Nomads United A...",
    "away_team": "Christchurch Uni...",
    "odds_home": 1.88,
    "odds_draw": 4.00,
    "odds_away": 2.90
  },
  {
    "time": "27 Jun, 03:45",
    "league": "Australia - South Australia State League 1...",
    "home_team": "Adelaide Atletico...",
    "away_team": "Adelaide Blue Ea...",
    "odds_home": 3.50,
    "odds_draw": 3.75,
    "odds_away": 1.83
  },
  {
    "time": "27 Jun, 04:00",
    "league": "International - World Cup",
    "home_team": "Egypt",
    "away_team": "IR Iran",
    "odds_home": 2.54,
    "odds_draw": 2.73,
    "odds_away": 3.84
  },
  {
    "time": "27 Jun, 04:00",
    "league": "New Zealand - National League",
    "home_team": "Auckland United ...",
    "away_team": "Melville United A...",
    "odds_home": 1.23,
    "odds_draw": 5.10,
    "odds_away": 8.10
  },
  {
    "time": "27 Jun, 04:00",
    "league": "New Zealand - National League",
    "home_team": "Eastern Suburbs ...",
    "away_team": "Birkenhead Unite...",
    "odds_home": 3.10,
    "odds_draw": 3.20,
    "odds_away": 2.00
  },
  {
    "time": "27 Jun, 04:00",
    "league": "Australia - U20 NSW NPL",
    "home_team": "University of NSW",
    "away_team": "Sutherland Shark...",
    "odds_home": 2.55,
    "odds_draw": 3.60,
    "odds_away": 2.35
  },
  {
    "time": "27 Jun, 04:00",
    "league": "Japan - Nadeshiko League, Div 2, Women",
    "home_team": "Nankatsu SC",
    "away_team": "Diosa Izumo FC",
    "odds_home": 5.10,
    "odds_draw": 3.50,
    "odds_away": 1.62
  },
  {
    "time": "27 Jun, 04:00",
    "league": "Australia - U23 Victoria NPL",
    "home_team": "Benteleigh Greens...",
    "away_team": "Altona Magic SC",
    "odds_home": 1.65,
    "odds_draw": 4.10,
    "odds_away": 3.60
  },
  {
    "time": "27 Jun, 04:00",
    "league": "Australia - U23 Victoria Premier League 1",
    "home_team": "Melbourne Knight...",
    "away_team": "Northcote City FC",
    "odds_home": 2.35,
    "odds_draw": 4.00,
    "odds_away": 2.20
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia NPL, Reserves",
    "home_team": "Campbelltown Ci...",
    "away_team": "West Adelaide S...",
    "odds_home": 1.12,
    "odds_draw": 7.40,
    "odds_away": 13.50
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia NPL, Reserves",
    "home_team": "Para Hills Knight...",
    "away_team": "North Eastern M...",
    "odds_home": 5.40,
    "odds_draw": 5.10,
    "odds_away": 1.40
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia NPL, Reserves",
    "home_team": "Playford City Res...",
    "away_team": "FK Beograd Rese...",
    "odds_home": 4.75,
    "odds_draw": 5.00,
    "odds_away": 1.45
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia State League 1",
    "home_team": "Adelaide Croatia",
    "away_team": "Adelaide Cobras",
    "odds_home": 1.79,
    "odds_draw": 4.50,
    "odds_away": 3.10
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia State League 1, ...",
    "home_team": "Modbury Jets SC...",
    "away_team": "Adelaide Olympi...",
    "odds_home": 2.95,
    "odds_draw": 4.30,
    "odds_away": 1.89
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia State League 1, ...",
    "home_team": "Salisbury United ...",
    "away_team": "The Cove FC Res...",
    "odds_home": 5.20,
    "odds_draw": 4.80,
    "odds_away": 1.43
  },
  {
    "time": "27 Jun, 04:15",
    "league": "Australia - South Australia State League 1, ...",
    "home_team": "South Adelaide R...",
    "away_team": "Fulham United F...",
    "odds_home": 2.25,
    "odds_draw": 4.20,
    "odds_away": 2.40
  },
  {
    "time": "27 Jun, 04:30",
    "league": "Australia - South Australia NPL, Reserves, ...",
    "home_team": "Salisbury Inter R...",
    "away_team": "Adelaide Univers...",
    "odds_home": 4.40,
    "odds_draw": 4.50,
    "odds_away": 1.48
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Australia - Northern NSW NPL",
    "home_team": "Charlestown Azz...",
    "away_team": "Belmont Swanse...",
    "odds_home": 2.55,
    "odds_draw": 3.60,
    "odds_away": 2.35
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Australia - Northern NSW NPL",
    "home_team": "Edgeworth FC",
    "away_team": "Adamstown Rose...",
    "odds_home": 1.71,
    "odds_draw": 3.90,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Australia - Northern NSW NPL",
    "home_team": "Newcastle Olym...",
    "away_team": "Cooks Hill United",
    "odds_home": 2.45,
    "odds_draw": 3.80,
    "odds_away": 2.30
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Australia - Tasmania NPL",
    "home_team": "South Hobart FC",
    "away_team": "Glenorchy Knight...",
    "odds_home": 1.41,
    "odds_draw": 4.60,
    "odds_away": 5.75
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Russia - 2. Liga, Division B, Group 3",
    "home_team": "Ska-Khabarovsk-2",
    "away_team": "Rotor II Volgograd",
    "odds_home": 1.91,
    "odds_draw": 3.60,
    "odds_away": 3.33
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Japan - Nadeshiko League, Div 2, Women",
    "home_team": "Speranza FC Osa...",
    "away_team": "Yamato Sylphid ...",
    "odds_home": 1.43,
    "odds_draw": 3.90,
    "odds_away": 7.00
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Japan - Nadeshiko League, Div. 1, Women",
    "home_team": "Iga FC Kunoichi",
    "away_team": "Viamaterasu Miy...",
    "odds_home": 2.30,
    "odds_draw": 3.20,
    "odds_away": 2.65
  },
  {
    "time": "27 Jun, 05:00",
    "league": "Australia - U23 Western Australia NPL",
    "home_team": "Bayswater City SC",
    "away_team": "Perth Redstar FC",
    "odds_home": 2.00,
    "odds_draw": 3.60,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 05:30",
    "league": "Australia - Capital NPL 1",
    "home_team": "O Connor Knight...",
    "away_team": "Canberra Olympic",
    "odds_home": 3.60,
    "odds_draw": 4.10,
    "odds_away": 1.74
  },
  {
    "time": "27 Jun, 05:30",
    "league": "Australia - Queensland NPL",
    "home_team": "Magic United Tfa",
    "away_team": "Brisbane City FC",
    "odds_home": 4.80,
    "odds_draw": 4.75,
    "odds_away": 1.51
  },
  {
    "time": "27 Jun, 05:30",
    "league": "Australia - Tasmania NPL",
    "home_team": "Clarence Zebras ...",
    "away_team": "Launceston Unite...",
    "odds_home": 1.26,
    "odds_draw": 5.60,
    "odds_away": 7.90
  },
  {
    "time": "27 Jun, 05:30",
    "league": "Australia - Tasmania NPL",
    "home_team": "Riverside Olympi...",
    "away_team": "Ulverstone FC",
    "odds_home": 1.39,
    "odds_draw": 4.80,
    "odds_away": 5.75
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - NSW NPL 1",
    "home_team": "University of NSW",
    "away_team": "Sutherland Sharks",
    "odds_home": 2.10,
    "odds_draw": 3.40,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - NSW NPL 1",
    "home_team": "Western Sydney ...",
    "away_team": "Manly United FC",
    "odds_home": 2.15,
    "odds_draw": 3.33,
    "odds_away": 2.95
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Capital NPL, Women",
    "home_team": "Tuggeranong Uni...",
    "away_team": "Canberra Olympic",
    "odds_home": 13.00,
    "odds_draw": 5.90,
    "odds_away": 1.13
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Victoria NPL, Women",
    "home_team": "Essendon Royals ...",
    "away_team": "FC Bulleen Lions",
    "odds_home": 2.10,
    "odds_draw": 3.60,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Victoria NPL, Women",
    "home_team": "Keilor Park SC",
    "away_team": "Melbourne Victo...",
    "odds_home": 3.90,
    "odds_draw": 3.80,
    "odds_away": 1.71
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - U23 Victoria NPL",
    "home_team": "Dandenong City SC",
    "away_team": "Avondale FC",
    "odds_home": 4.70,
    "odds_draw": 4.40,
    "odds_away": 1.45
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - U23 Western Australia NPL",
    "home_team": "Armadale SC",
    "away_team": "Perth SC",
    "odds_home": 5.50,
    "odds_draw": 5.00,
    "odds_away": 1.34
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - U23 Western Australia NPL",
    "home_team": "Fremantle City FC",
    "away_team": "Western Knights",
    "odds_home": 1.41,
    "odds_draw": 4.90,
    "odds_away": 4.70
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - U23 Western Australia NPL",
    "home_team": "Olympic Kingswa...",
    "away_team": "Balcatta Etna FC",
    "odds_home": 1.45,
    "odds_draw": 4.20,
    "odds_away": 4.90
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Floreat Athena F...",
    "away_team": "Inglewood Unite...",
    "odds_home": 1.29,
    "odds_draw": 5.25,
    "odds_away": 7.30
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Gwelup Croatia S...",
    "away_team": "Curtin University...",
    "odds_home": 1.54,
    "odds_draw": 4.25,
    "odds_away": 4.60
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Mandurah City F...",
    "away_team": "Kingsley Westsid...",
    "odds_home": 2.85,
    "odds_draw": 3.60,
    "odds_away": 2.10
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Quinns FC Reserve",
    "away_team": "Murdoch Univers...",
    "odds_home": 1.48,
    "odds_draw": 4.30,
    "odds_away": 5.25
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Subiaco AFC Res...",
    "away_team": "Joondalop City F...",
    "odds_home": 6.40,
    "odds_draw": 4.70,
    "odds_away": 1.37
  },
  {
    "time": "27 Jun, 06:00",
    "league": "Australia - Western Australia State League...",
    "home_team": "Uwa Nedlands F...",
    "away_team": "Cockburn City S...",
    "odds_home": 1.71,
    "odds_draw": 3.90,
    "odds_away": 3.87
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - South Australia NPL",
    "home_team": "Para Hills Knight...",
    "away_team": "North Eastern M...",
    "odds_home": 22.00,
    "odds_draw": 13.00,
    "odds_away": 1.02
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - South Australia NPL",
    "home_team": "Playford City",
    "away_team": "FK Beograd",
    "odds_home": 2.25,
    "odds_draw": 3.40,
    "odds_away": 2.75
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - South Australia State League 1",
    "home_team": "Adelaide Croatia ...",
    "away_team": "Adelaide Cobras",
    "odds_home": 1.64,
    "odds_draw": 4.20,
    "odds_away": 4.00
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - South Australia State League 1",
    "home_team": "Adelaide Victory",
    "away_team": "Adelaide Blue Ea...",
    "odds_home": 2.75,
    "odds_draw": 3.75,
    "odds_away": 2.10
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - South Australia State League 1",
    "home_team": "Modbury Jets SC",
    "away_team": "Adelaide Olympic...",
    "odds_home": 1.68,
    "odds_draw": 4.00,
    "odds_away": 3.90
  },
  {
    "time": "27 Jun, 06:30",
    "league": "Australia - Victoria NPL, Women",
    "home_team": "South Melbourne...",
    "away_team": "Box Hill United",
    "odds_home": 2.05,
    "odds_draw": 3.70,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 06:45",
    "league": "Australia - South Australia NPL, Women",
    "home_team": "Salisbury Inter",
    "away_team": "Adelaide Univers...",
    "odds_home": 1.15,
    "odds_draw": 7.20,
    "odds_away": 10.50
  },
  {
    "time": "27 Jun, 06:45",
    "league": "Australia - U23 Queensland Premier League...",
    "home_team": "Broadbeach United",
    "away_team": "Capalaba FC",
    "odds_home": 1.58,
    "odds_draw": 4.10,
    "odds_away": 4.00
  },
  {
    "time": "27 Jun, 06:45",
    "league": "Australia - U23 Queensland Premier League...",
    "home_team": "Sunshine Coast...",
    "away_team": "Robina City",
    "odds_home": 2.00,
    "odds_draw": 3.80,
    "odds_away": 2.70
  },
  {
    "time": "27 Jun, 06:45",
    "league": "Australia - U23 Victoria NPL",
    "home_team": "Caroline Springs...",
    "away_team": "Preston Lions FC",
    "odds_home": 1.62,
    "odds_draw": 4.00,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 07:00",
    "league": "Australia - Queensland NPL",
    "home_team": "Peninsula Power ...",
    "away_team": "Brisbane Roar FC",
    "odds_home": 1.23,
    "odds_draw": 6.25,
    "odds_away": 9.10
  },
  {
    "time": "27 Jun, 07:30",
    "league": "Australia - NSW League One",
    "home_team": "Northern Tigers",
    "away_team": "Dulwich Hill",
    "odds_home": 1.66,
    "odds_draw": 3.90,
    "odds_away": 4.10
  },
  {
    "time": "27 Jun, 07:30",
    "league": "Australia - Queensland Premier League 1",
    "home_team": "St George Willa...",
    "away_team": "North Star FC",
    "odds_home": 3.25,
    "odds_draw": 3.90,
    "odds_away": 1.86
  },
  {
    "time": "27 Jun, 07:30",
    "league": "Australia - U20 NSW NPL",
    "home_team": "St George FC",
    "away_team": "Sydney Olympic ...",
    "odds_home": 1.71,
    "odds_draw": 4.00,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 07:30",
    "league": "Australia - Northern NSW NPL, Women",
    "home_team": "New Lambton FC",
    "away_team": "Maitland FC",
    "odds_home": 6.70,
    "odds_draw": 5.90,
    "odds_away": 1.28
  },
  {
    "time": "27 Jun, 07:45",
    "league": "Australia - Tasmania Super League, Women",
    "home_team": "Riverside Olympic",
    "away_team": "Launceston United",
    "odds_home": 24.00,
    "odds_draw": 10.00,
    "odds_away": 1.04
  },
  {
    "time": "27 Jun, 07:45",
    "league": "Australia - U23 Queensland NPL",
    "home_team": "Eastern Suburbs",
    "away_team": "Olympic Football...",
    "odds_home": 1.62,
    "odds_draw": 4.10,
    "odds_away": 3.75
  },
  {
    "time": "27 Jun, 07:45",
    "league": "Australia - U23 Queensland NPL",
    "home_team": "Dandenong Thun...",
    "away_team": "Hume City",
    "odds_home": 5.75,
    "odds_draw": 4.50,
    "odds_away": 1.43
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW NPL 1",
    "home_team": "SD Raiders FC",
    "away_team": "St George City FA",
    "odds_home": 2.50,
    "odds_draw": 3.20,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia NPL",
    "home_team": "Armadale SC",
    "away_team": "Perth SC",
    "odds_home": 2.95,
    "odds_draw": 4.00,
    "odds_away": 1.95
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia NPL",
    "home_team": "Fremantle City",
    "away_team": "Western Knights ...",
    "odds_home": 2.35,
    "odds_draw": 3.80,
    "odds_away": 2.40
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia NPL",
    "home_team": "Olympic Kingswa...",
    "away_team": "Balcatta",
    "odds_home": 1.32,
    "odds_draw": 5.10,
    "odds_away": 6.80
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia NPL",
    "home_team": "Perth Glory FC",
    "away_team": "Stirling Macedon...",
    "odds_home": 3.40,
    "odds_draw": 3.75,
    "odds_away": 1.85
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Republic of Korea - K3 League",
    "home_team": "Changwon City FC",
    "away_team": "Yeoju Citizen FC",
    "odds_home": 1.92,
    "odds_draw": 3.10,
    "odds_away": 3.90
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Republic of Korea - K3 League",
    "home_team": "Siheung Citizen FC",
    "away_team": "Jeonbuk FC II",
    "odds_home": 1.29,
    "odds_draw": 5.00,
    "odds_away": 8.20
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League One",
    "home_team": "Canterbury Bank...",
    "away_team": "Central Coast Ma...",
    "odds_home": 1.88,
    "odds_draw": 3.60,
    "odds_away": 3.40
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League One",
    "home_team": "Hurstville FC",
    "away_team": "Hills United FC B...",
    "odds_home": 2.45,
    "odds_draw": 3.50,
    "odds_away": 2.45
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League One",
    "home_team": "Inter Lions FC",
    "away_team": "Newcastle Jets Y...",
    "odds_home": 2.50,
    "odds_draw": 3.75,
    "odds_away": 2.30
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League Two",
    "home_team": "Central Coast Un...",
    "away_team": "Gladesville Ryde ...",
    "odds_home": 1.71,
    "odds_draw": 4.00,
    "odds_away": 3.75
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League Two",
    "home_team": "Inner West Hawk...",
    "away_team": "Hawkesbury City...",
    "odds_home": 2.50,
    "odds_draw": 3.90,
    "odds_away": 2.25
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - NSW League Two",
    "home_team": "Parramatta FC Ea...",
    "away_team": "Nepean FC",
    "odds_home": 1.72,
    "odds_draw": 4.00,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Japan - Nadeshiko League, Div. 1, Women",
    "home_team": "Nittaidai FC",
    "away_team": "Orca Kamogawa ...",
    "odds_home": 6.10,
    "odds_draw": 3.90,
    "odds_away": 1.41
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Japan - Nadeshiko League, Div. 1, Women",
    "home_team": "Sfida Setagaya FC",
    "away_team": "Nippatsu Yokoha...",
    "odds_home": 2.15,
    "odds_draw": 3.25,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Korea Rep - Korea Republic K4 League",
    "home_team": "Jinju Citizen FC",
    "away_team": "Seosan FC",
    "odds_home": 1.16,
    "odds_draw": 6.40,
    "odds_away": 12.00
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Queensland Premier League 3 ...",
    "home_team": "AC Carina",
    "away_team": "North Lakes United",
    "odds_home": 1.63,
    "odds_draw": 4.40,
    "odds_away": 3.50
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Queensland Premier League 3 ...",
    "home_team": "Springfield United",
    "away_team": "Newmarket SFC",
    "odds_home": 3.60,
    "odds_draw": 4.50,
    "odds_away": 1.60
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia State League 1",
    "home_team": "Subiaco AFC",
    "away_team": "Joondalup City",
    "odds_home": 3.30,
    "odds_draw": 3.90,
    "odds_away": 1.85
  },
  {
    "time": "27 Jun, 08:00",
    "league": "Australia - Western Australia State League 1",
    "home_team": "UWA Nedlands FC",
    "away_team": "Cockburn City",
    "odds_home": 1.30,
    "odds_draw": 5.20,
    "odds_away": 7.25
  },
  {
    "time": "27 Jun, 08:30",
    "league": "Australia - NSW NPL 1",
    "home_team": "NWS Spirit",
    "away_team": "Wollongong Wol...",
    "odds_home": 1.99,
    "odds_draw": 3.20,
    "odds_away": 3.50
  },
  {
    "time": "27 Jun, 08:30",
    "league": "China - China League 1",
    "home_team": "Changchun Yatai",
    "away_team": "Guangxi Hengch...",
    "odds_home": 3.00,
    "odds_draw": 3.10,
    "odds_away": 2.35
  },
  {
    "time": "27 Jun, 08:30",
    "league": "New Zealand - National League",
    "home_team": "Auckland FC Res...",
    "away_team": "Manukau United ...",
    "odds_home": 1.24,
    "odds_draw": 5.00,
    "odds_away": 8.00
  },
  {
    "time": "27 Jun, 08:30",
    "league": "Australia - South Australia NPL, Women",
    "home_team": "Campbelltown Ci...",
    "away_team": "West Adelaide",
    "odds_home": 7.50,
    "odds_draw": 6.75,
    "odds_away": 1.22
  },
  {
    "time": "27 Jun, 08:30",
    "league": "Australia - South Australia NPL, Women",
    "home_team": "Metrostars",
    "away_team": "Modbury Vista",
    "odds_home": 3.10,
    "odds_draw": 4.30,
    "odds_away": 1.83
  },
  {
    "time": "27 Jun, 08:45",
    "league": "Australia - Capital NPL 1",
    "home_team": "Monaro Panthers...",
    "away_team": "Cooma Tigers",
    "odds_home": 2.25,
    "odds_draw": 3.90,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 09:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Uta Arad",
    "away_team": "CSC Dumbravita",
    "odds_home": 1.48,
    "odds_draw": 3.60,
    "odds_away": 6.30
  },
  {
    "time": "27 Jun, 09:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Vion Zlate Mo...",
    "away_team": "MFk Dukla Bansk...",
    "odds_home": 4.10,
    "odds_draw": 4.00,
    "odds_away": 1.60
  },
  {
    "time": "27 Jun, 09:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FK Viktoria Zizkov",
    "away_team": "SK Slavia Prague B",
    "odds_home": 2.30,
    "odds_draw": 3.60,
    "odds_away": 2.50
  },
  {
    "time": "27 Jun, 09:00",
    "league": "Australia - Victoria NPL, Women",
    "home_team": "Caroline Springs ...",
    "away_team": "Preston Lions FC",
    "odds_home": 4.40,
    "odds_draw": 3.75,
    "odds_away": 1.64
  },
  {
    "time": "27 Jun, 09:00",
    "league": "Australia - Queensland Premier League 1 ...",
    "home_team": "Broadbeach United",
    "away_team": "Capalaba Bulldogs",
    "odds_home": 1.08,
    "odds_draw": 7.80,
    "odds_away": 22.00
  },
  {
    "time": "27 Jun, 09:00",
    "league": "Australia - Queensland Premier League 1 ...",
    "home_team": "Sunshine Coast ...",
    "away_team": "Robina City",
    "odds_home": 2.15,
    "odds_draw": 3.75,
    "odds_away": 2.75
  },
  {
    "time": "27 Jun, 09:00",
    "league": "China - China League 2",
    "home_team": "Changchun Xidu",
    "away_team": "Nantong Haimen ...",
    "odds_home": 4.40,
    "odds_draw": 2.95,
    "odds_away": 1.77
  },
  {
    "time": "27 Jun, 09:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "1. SK Prostejov",
    "away_team": "SFC Opava",
    "odds_home": 3.40,
    "odds_draw": 3.25,
    "odds_away": 1.97
  },
  {
    "time": "27 Jun, 09:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "AS Trencin",
    "away_team": "FC Petrzalka",
    "odds_home": 1.57,
    "odds_draw": 4.00,
    "odds_away": 4.50
  },
  {
    "time": "27 Jun, 09:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Lugano",
    "away_team": "Neuchatel Xamax",
    "odds_home": 1.43,
    "odds_draw": 4.40,
    "odds_away": 5.40
  },
  {
    "time": "27 Jun, 09:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "TSV Hartberg",
    "away_team": "FC Admira Wack...",
    "odds_home": 1.37,
    "odds_draw": 4.50,
    "odds_away": 6.40
  },
  {
    "time": "27 Jun, 09:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Viktoria Plzen",
    "away_team": "SK Artis Brno",
    "odds_home": 1.48,
    "odds_draw": 4.20,
    "odds_away": 5.20
  },
  {
    "time": "27 Jun, 09:30",
    "league": "Australia - NSW NPL 1",
    "home_team": "St George Saints ...",
    "away_team": "Sydney Olympic ...",
    "odds_home": 1.69,
    "odds_draw": 3.70,
    "odds_away": 4.25
  },
  {
    "time": "27 Jun, 09:30",
    "league": "Australia - U20 NSW League One",
    "home_team": "Macarthur Rams ...",
    "away_team": "Hakoah Sydney C...",
    "odds_home": 3.20,
    "odds_draw": 3.90,
    "odds_away": 1.79
  },
  {
    "time": "27 Jun, 09:30",
    "league": "Australia - U20 NSW League One",
    "home_team": "Northern Tigers FC",
    "away_team": "Dulwich Hill",
    "odds_home": 1.51,
    "odds_draw": 4.10,
    "odds_away": 4.50
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Utrecht",
    "away_team": "De Graafschap",
    "odds_home": 1.30,
    "odds_draw": 5.40,
    "odds_away": 6.50
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Vysocina Jihl...",
    "away_team": "FK Pribram",
    "odds_home": 2.80,
    "odds_draw": 3.30,
    "odds_away": 2.20
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FK Teplice",
    "away_team": "Spartak Trnava",
    "odds_home": 1.78,
    "odds_draw": 3.75,
    "odds_away": 3.60
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "MFK Tatran Lipto...",
    "away_team": "Podhale Nowy Targ",
    "odds_home": 1.99,
    "odds_draw": 3.60,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "MSK Povazska B...",
    "away_team": "FC Banik Ostrava B",
    "odds_home": 2.55,
    "odds_draw": 3.33,
    "odds_away": 2.40
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SK Sigma Olomouc",
    "away_team": "MFK Ruzomberok",
    "odds_home": 2.00,
    "odds_draw": 3.60,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 10:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "TSV Steinbach H...",
    "away_team": "Sportfreunde Eis...",
    "odds_home": 1.26,
    "odds_draw": 5.50,
    "odds_away": 7.40
  },
  {
    "time": "27 Jun, 10:00",
    "league": "Australia - Queensland NPL",
    "home_team": "Eastern Suburbs ...",
    "away_team": "Olympic FC Brisb...",
    "odds_home": 1.88,
    "odds_draw": 3.90,
    "odds_away": 3.40
  },
  {
    "time": "27 Jun, 10:00",
    "league": "Australia - Queensland Premier League 1, ...",
    "home_team": "Grange Thistle",
    "away_team": "Logan Lightning",
    "odds_home": 2.25,
    "odds_draw": 3.80,
    "odds_away": 2.35
  },
  {
    "time": "27 Jun, 10:00",
    "league": "Australia - U20 NSW League One",
    "home_team": "Hurstville FC",
    "away_team": "Hills United FC",
    "odds_home": 2.70,
    "odds_draw": 3.70,
    "odds_away": 2.05
  },
  {
    "time": "27 Jun, 10:15",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Zlin",
    "away_team": "MFK Skalica",
    "odds_home": 1.66,
    "odds_draw": 3.90,
    "odds_away": 4.00
  },
  {
    "time": "27 Jun, 10:15",
    "league": "Australia - Queensland Premier League 3 M...",
    "home_team": "UQ FC",
    "away_team": "Moggill FC",
    "odds_home": 4.80,
    "odds_draw": 4.90,
    "odds_away": 1.39
  },
  {
    "time": "27 Jun, 10:30",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "FC Zurich",
    "away_team": "FC Schaffhausen",
    "odds_home": 1.27,
    "odds_draw": 5.00,
    "odds_away": 8.70
  },
  {
    "time": "27 Jun, 10:45",
    "league": "Australia - U20 NSW NPL",
    "home_team": "NWS Spirit FC",
    "away_team": "Wollongong Wol...",
    "odds_home": 1.96,
    "odds_draw": 3.90,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Australia - South Australia State League 1 ...",
    "home_team": "West Torrens Bir...",
    "away_team": "Sturt Lions Reser...",
    "odds_home": 1.97,
    "odds_draw": 4.25,
    "odds_away": 2.80
  },
  {
    "time": "27 Jun, 11:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Esbjerg FB",
    "away_team": "Vejle BK",
    "odds_home": 2.05,
    "odds_draw": 4.00,
    "odds_away": 2.65
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Republic of Korea - K3 League",
    "home_team": "Chuncheon FC",
    "away_team": "Yangpyeong FC",
    "odds_home": 2.40,
    "odds_draw": 3.00,
    "odds_away": 2.90
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Republic of Korea - K3 League",
    "home_team": "Ulsan Citizen FC",
    "away_team": "FC Mokpo",
    "odds_home": 2.35,
    "odds_draw": 2.90,
    "odds_away": 3.10
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Republic of Korea - WK-League",
    "home_team": "Boeun Sangmu ...",
    "away_team": "Incheon Hyundai ...",
    "odds_home": 3.50,
    "odds_draw": 3.10,
    "odds_away": 1.92
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Republic of Korea - WK-League",
    "home_team": "Changnyeong WFC",
    "away_team": "Sejong Sportstot...",
    "odds_home": 3.30,
    "odds_draw": 3.20,
    "odds_away": 1.96
  },
  {
    "time": "27 Jun, 11:00",
    "league": "Korea Rep - Korea Republic K4 League",
    "home_team": "Pyeongtaek Citiz...",
    "away_team": "Seoul Jungnang FC",
    "odds_home": 4.00,
    "odds_draw": 3.90,
    "odds_away": 1.69
  },
  {
    "time": "27 Jun, 12:00",
    "league": "China - Chinese Super League",
    "home_team": "Liaoning Tieren FC",
    "away_team": "Shandong Taisha...",
    "odds_home": 2.90,
    "odds_draw": 3.80,
    "odds_away": 2.27
  },
  {
    "time": "27 Jun, 12:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Paksi FC",
    "away_team": "KFC Komarno",
    "odds_home": 1.63,
    "odds_draw": 4.25,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 12:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Rakow Czestoch...",
    "away_team": "GKS Piast Gliwice",
    "odds_home": 1.79,
    "odds_draw": 3.60,
    "odds_away": 3.60
  },
  {
    "time": "27 Jun, 12:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "SK Rapid",
    "away_team": "FAC Wien",
    "odds_home": 1.45,
    "odds_draw": 4.40,
    "odds_away": 5.20
  },
  {
    "time": "27 Jun, 12:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Widzew Lodz",
    "away_team": "ZKS Stal Rzeszow",
    "odds_home": 1.41,
    "odds_draw": 4.40,
    "odds_away": 5.80
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Ettan",
    "home_team": "FC Stockholm Int...",
    "away_team": "Enkopings SK",
    "odds_home": 1.45,
    "odds_draw": 4.50,
    "odds_away": 5.90
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Ettan",
    "home_team": "FC Trollhattan",
    "away_team": "Angelholms FF",
    "odds_home": 2.15,
    "odds_draw": 3.60,
    "odds_away": 2.90
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Ettan",
    "home_team": "Laholms FK",
    "away_team": "Utsiktens BK",
    "odds_home": 1.73,
    "odds_draw": 3.90,
    "odds_away": 4.10
  },
  {
    "time": "27 Jun, 12:00",
    "league": "China - China League 1",
    "home_team": "Dalian Kun City",
    "away_team": "Shenzhen Junior...",
    "odds_home": 2.20,
    "odds_draw": 3.30,
    "odds_away": 3.20
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Finland - Veikkausliiga",
    "home_team": "Tampereen Ilves",
    "away_team": "Seinäjoen JK",
    "odds_home": 2.30,
    "odds_draw": 3.70,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Division 2",
    "home_team": "IFK Haninge",
    "away_team": "IK Sleipner",
    "odds_home": 2.00,
    "odds_draw": 3.80,
    "odds_away": 2.50
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Division 2",
    "home_team": "IFK Umea",
    "away_team": "Storfors AIK",
    "odds_home": 4.40,
    "odds_draw": 4.20,
    "odds_away": 1.57
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Sweden - Division 2",
    "home_team": "IK Franke",
    "away_team": "Viggbyholms IK FF",
    "odds_home": 1.64,
    "odds_draw": 4.00,
    "odds_away": 4.10
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Norway - 2nd Division Group 1",
    "home_team": "FK Vidar",
    "away_team": "Kvik Halden FK",
    "odds_home": 3.70,
    "odds_draw": 3.80,
    "odds_away": 1.82
  },
  {
    "time": "27 Jun, 12:00",
    "league": "Norway - 2nd Division Group 2",
    "home_team": "Ullensaker/Kisa",
    "away_team": "Rana FK",
    "odds_home": 2.20,
    "odds_draw": 3.75,
    "odds_away": 2.80
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 1",
    "home_team": "Foshan Nanshi FC",
    "away_team": "Yanbian Longding",
    "odds_home": 2.85,
    "odds_draw": 2.95,
    "odds_away": 2.65
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 1",
    "home_team": "Guandong GZ-Po...",
    "away_team": "Shaanxi Union FC",
    "odds_home": 1.93,
    "odds_draw": 3.33,
    "odds_away": 3.90
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 1",
    "home_team": "Nantong Zhiyun",
    "away_team": "Meizhou Hakka",
    "odds_home": 1.48,
    "odds_draw": 4.20,
    "odds_away": 6.40
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 1",
    "home_team": "Shijiazhuang Kun...",
    "away_team": "Nanjing City",
    "odds_home": 2.90,
    "odds_draw": 3.00,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 2",
    "home_team": "Guangdong Mingtu",
    "away_team": "Xiamen Feilu",
    "odds_home": 2.55,
    "odds_draw": 2.90,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 2",
    "home_team": "Hubei Istar",
    "away_team": "Guizhou Zhuchen...",
    "odds_home": 2.80,
    "odds_draw": 3.10,
    "odds_away": 2.25
  },
  {
    "time": "27 Jun, 12:30",
    "league": "China - China League 2",
    "home_team": "Lanzhou Longyua...",
    "away_team": "Dalian Yingbo B",
    "odds_home": 2.55,
    "odds_draw": 2.90,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 12:30",
    "league": "Belarus - Vysshaya Liga",
    "home_team": "FC Torpedo Bela...",
    "away_team": "Bate Borisov",
    "odds_home": 1.65,
    "odds_draw": 3.70,
    "odds_away": 5.25
  },
  {
    "time": "27 Jun, 12:30",
    "league": "Norway - 2nd Division Group 1",
    "home_team": "Mjoendalen IF",
    "away_team": "Bjarg",
    "odds_home": 1.81,
    "odds_draw": 3.90,
    "odds_away": 3.60
  },
  {
    "time": "27 Jun, 12:35",
    "league": "China - Chinese Super League",
    "home_team": "Henan",
    "away_team": "Shanghai Port FC",
    "odds_home": 2.20,
    "odds_draw": 3.40,
    "odds_away": 3.27
  },
  {
    "time": "27 Jun, 12:35",
    "league": "China - Chinese Super League",
    "home_team": "Shenzhen Peng C...",
    "away_team": "Chengdu Rongch...",
    "odds_home": 4.30,
    "odds_draw": 3.90,
    "odds_away": 1.77
  },
  {
    "time": "27 Jun, 13:00",
    "league": "China - Chinese Super League",
    "home_team": "Beijing Guoan",
    "away_team": "Wuhan Three To...",
    "odds_home": 1.35,
    "odds_draw": 5.70,
    "odds_away": 7.60
  },
  {
    "time": "27 Jun, 13:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "NK Celje",
    "away_team": "Shkendija Tetovo",
    "odds_home": 1.97,
    "odds_draw": 3.25,
    "odds_away": 4.30
  },
  {
    "time": "27 Jun, 13:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Nordsjaelland",
    "away_team": "AC Horsens",
    "odds_home": 1.71,
    "odds_draw": 3.75,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Sweden - Division 2",
    "home_team": "IFK Luleaa",
    "away_team": "Skellefteaa FF",
    "odds_home": 2.15,
    "odds_draw": 3.60,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Norway - 3. Division, Group 3",
    "home_team": "Kjelsaas",
    "away_team": "Hoenefoss BK",
    "odds_home": 1.86,
    "odds_draw": 3.80,
    "odds_away": 3.40
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Norway - 3. Division, Group 3",
    "home_team": "Lorenskog IF",
    "away_team": "Grorud IL",
    "odds_home": 2.20,
    "odds_draw": 3.60,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Lithuania - 1 Lyga",
    "home_team": "Hegeklann Litau...",
    "away_team": "FK Jonava",
    "odds_home": 4.25,
    "odds_draw": 3.80,
    "odds_away": 1.67
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Finland - Kakkonen",
    "home_team": "GBK Kokkola",
    "away_team": "JS Hercules",
    "odds_home": 1.49,
    "odds_draw": 4.90,
    "odds_away": 4.60
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Kazakhstan - Premier League",
    "home_team": "FC Okzhetpes",
    "away_team": "FC Kairaat Almaty",
    "odds_home": 3.70,
    "odds_draw": 3.60,
    "odds_away": 1.85
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Sweden - Damallsvenskan",
    "home_team": "Malmo FF",
    "away_team": "Kristianstads DFF",
    "odds_home": 1.57,
    "odds_draw": 3.70,
    "odds_away": 4.50
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Finland - Kansallinen Liiga, Women",
    "home_team": "IF Gnistan",
    "away_team": "PK-35 Vantaa",
    "odds_home": 2.80,
    "odds_draw": 3.70,
    "odds_away": 2.00
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Ireland - Premier Division, Women",
    "home_team": "Shamrock Rovers...",
    "away_team": "Wexford Youths ...",
    "odds_home": 1.66,
    "odds_draw": 3.90,
    "odds_away": 4.10
  },
  {
    "time": "27 Jun, 13:00",
    "league": "Finland - Kolmonien",
    "home_team": "Mikkelin Pallo-Ki...",
    "away_team": "Kopa",
    "odds_home": 1.30,
    "odds_draw": 5.50,
    "odds_away": 6.75
  },
  {
    "time": "27 Jun, 13:30",
    "league": "Malawi - Super League",
    "home_team": "Chitipa United",
    "away_team": "Kamuzu Barracks...",
    "odds_home": 2.55,
    "odds_draw": 2.95,
    "odds_away": 2.70
  },
  {
    "time": "27 Jun, 13:30",
    "league": "Malawi - Super League",
    "home_team": "Mitundu Baptist",
    "away_team": "Blue Eagles Malawi",
    "odds_home": 4.25,
    "odds_draw": 3.10,
    "odds_away": 1.83
  },
  {
    "time": "27 Jun, 14:00",
    "league": "International Clubs - Club Friendly Games",
    "home_team": "Arbroath FC",
    "away_team": "St Mirren FC",
    "odds_home": 3.00,
    "odds_draw": 3.25,
    "odds_away": 2.15
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Sweden - Superettan",
    "home_team": "Ljungskile SK",
    "away_team": "Orebro SK",
    "odds_home": 1.92,
    "odds_draw": 3.75,
    "odds_away": 3.70
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Sweden - Superettan",
    "home_team": "Varbergs BolS",
    "away_team": "Osters IF",
    "odds_home": 1.86,
    "odds_draw": 3.75,
    "odds_away": 3.90
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Uruguay - Segunda Division",
    "home_team": "CA Atenas de Sa...",
    "away_team": "Tacua rembo FC",
    "odds_home": 2.55,
    "odds_draw": 2.80,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Finland - Ykkosliiga",
    "home_team": "FC Haka Valkeak...",
    "away_team": "FC KTP Kotka",
    "odds_home": 2.40,
    "odds_draw": 3.25,
    "odds_away": 2.80
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Finland - Ykkosliiga",
    "home_team": "JIPPO",
    "away_team": "Ekenas Idrottsfor...",
    "odds_home": 1.73,
    "odds_draw": 3.70,
    "odds_away": 4.40
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Sweden - Division 2",
    "home_team": "Taby FK",
    "away_team": "FC Gute",
    "odds_home": 1.66,
    "odds_draw": 3.90,
    "odds_away": 4.20
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Russia - 2. Liga, Division B, Group 3",
    "home_team": "FC Metallurg Lip...",
    "away_team": "Rodina-3 Moscow",
    "odds_home": 1.91,
    "odds_draw": 3.60,
    "odds_away": 3.37
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Norway - 2nd Division Group 1",
    "home_team": "Pors Grenland",
    "away_team": "Arendal FK",
    "odds_home": 2.35,
    "odds_draw": 3.60,
    "odds_away": 2.60
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Paraguay - Division Intermedia",
    "home_team": "Tacuary Asuncion",
    "away_team": "CA Tembetary Y...",
    "odds_home": 2.75,
    "odds_draw": 3.20,
    "odds_away": 2.35
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Lithuania - 1 Lyga",
    "home_team": "Dfk Dainava Alytus",
    "away_team": "FC Neptunas Klai...",
    "odds_home": 2.40,
    "odds_draw": 3.30,
    "odds_away": 2.65
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Lithuania - 1 Lyga",
    "home_team": "FK Ekranas",
    "away_team": "FK Atmosfera",
    "odds_home": 3.90,
    "odds_draw": 3.50,
    "odds_away": 1.80
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Lithuania - 1 Lyga",
    "home_team": "FK Transinvest B",
    "away_team": "FK Tauras Taurage",
    "odds_home": 7.10,
    "odds_draw": 5.20,
    "odds_away": 1.70
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Zimbabwe - Premier Soccer League",
    "home_team": "Caps United FC",
    "away_team": "Triangle United",
    "odds_home": 1.39,
    "odds_draw": 3.80,
    "odds_away": 8.50
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Zimbabwe - Premier Soccer League",
    "home_team": "Chicken Inn FC",
    "away_team": "Hardrock FC",
    "odds_home": 2.90,
    "odds_draw": 2.85,
    "odds_away": 2.45
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Finland - Kakkonen",
    "home_team": "Huima/Urho",
    "away_team": "Jakobstads Bollk...",
    "odds_home": 2.10,
    "odds_draw": 3.90,
    "odds_away": 2.80
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Finland - Kakkonen",
    "home_team": "Musan Salama",
    "away_team": "P-lirot",
    "odds_home": 4.70,
    "odds_draw": 4.50,
    "odds_away": 1.53
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Kazakhstan - Premier League",
    "home_team": "FC Zhetysu",
    "away_team": "FC Aktobe",
    "odds_home": 3.00,
    "odds_draw": 3.20,
    "odds_away": 2.25
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Russia - Superleague, Women",
    "home_team": "Zhfk Krylya Sove...",
    "away_team": "FK Rostov",
    "odds_home": 1.30,
    "odds_draw": 4.60,
    "odds_away": 9.10
  },
  {
    "time": "27 Jun, 14:00",
    "league": "Finland - Kolmonen",
    "home_team": "Helsingin Ponnist...",
    "away_team": "Tups",
    "odds_home": 4.50,
    "odds_draw": 4.60,
    "odds_away": 1.51
  },
  {
    "time": "27 Jun, 14:15",
    "league": "Faroe Islands - 1st deild",
    "home_team": "NSI Runavik II",
    "away_team": "B36 Torshavn II",
    "odds_home": 1.82,
    "odds_draw": 4.00,
    "odds_away": 3.40
  },
  {
    "time": "27 Jun, 14:30",
    "league": "Belarus - Vysshaya Liga",
    "home_team": "Maxline Vitebsk",
    "away_team": "Naftan Novopolo...",
    "odds_home": 1.11,
    "odds_draw": 7.70,
    "odds_away": 19.00
  },
  {
    "time": "27 Jun, 14:30",
    "league": "Russia - Superleague, Women",
    "home_team": "CSKA Moscow",
    "away_team": "FC Zenit Saint Pe...",
    "odds_home": 2.30,
    "odds_draw": 3.20,
    "odds_away": 2.85
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Norway - 1st Division",
    "home_team": "Sandnes Ulf",
    "away_team": "Raufoss IL",
    "odds_home": 1.74,
    "odds_draw": 4.00,
    "odds_away": 4.25
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Norway - 1st Division",
    "home_team": "Stabaek IF",
    "away_team": "Bryne FK",
    "odds_home": 1.81,
    "odds_draw": 4.10,
    "odds_away": 3.80
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Norway - 1st Division",
    "home_team": "Stroemmen IF",
    "away_team": "Moss FK",
    "odds_home": 2.55,
    "odds_draw": 3.70,
    "odds_away": 2.50
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Ettan",
    "home_team": "Aatvidabergs FF",
    "away_team": "FC Rosengaard 1...",
    "odds_home": 2.70,
    "odds_draw": 3.30,
    "odds_away": 2.40
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Ettan",
    "home_team": "Ariana FC",
    "away_team": "Jonkopings Sodr...",
    "odds_home": 2.65,
    "odds_draw": 3.30,
    "odds_away": 2.45
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Ettan",
    "home_team": "FC Arlanda",
    "away_team": "IF Karlstad Fotbol",
    "odds_home": 2.75,
    "odds_draw": 3.30,
    "odds_away": 2.40
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Ettan",
    "home_team": "Gefle IF",
    "away_team": "IFK Stocksund",
    "odds_home": 1.68,
    "odds_draw": 3.90,
    "odds_away": 4.20
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Ettan",
    "home_team": "Lunds BK",
    "away_team": "Skovde AIK",
    "odds_home": 1.65,
    "odds_draw": 3.80,
    "odds_away": 4.50
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Finland - Veikkausliiga",
    "home_team": "HJK Helsinki",
    "away_team": "Kuopion Palloseura",
    "odds_home": 2.30,
    "odds_draw": 3.60,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Finland - Veikkausliiga",
    "home_team": "IFK Mariehamn",
    "away_team": "FC Inter Turku",
    "odds_home": 8.90,
    "odds_draw": 5.40,
    "odds_away": 1.30
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Latvia - 1.Liga",
    "home_team": "FK Rfs II",
    "away_team": "Riga FC II",
    "odds_home": 2.30,
    "odds_draw": 3.70,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Astorps FF",
    "away_team": "Torslanda IK",
    "odds_home": 1.89,
    "odds_draw": 3.75,
    "odds_away": 3.30
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "BK Astrio",
    "away_team": "Hestrafors IF",
    "odds_home": 2.65,
    "odds_draw": 3.60,
    "odds_away": 2.25
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Bollstanas SK",
    "away_team": "Korsnas IF FK",
    "odds_home": 1.72,
    "odds_draw": 4.00,
    "odds_away": 3.75
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Falu BS FK",
    "away_team": "IFK Lidingo FK",
    "odds_home": 1.42,
    "odds_draw": 4.50,
    "odds_away": 5.70
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Husqvarna FF",
    "away_team": "IF K Lidingo FK",
    "odds_home": 1.42,
    "odds_draw": 4.50,
    "odds_away": 5.70
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "IF Eker Orebro",
    "away_team": "FOC Farsta",
    "odds_home": 3.10,
    "odds_draw": 3.90,
    "odds_away": 1.92
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Motala AIF FK",
    "away_team": "Vandersborgs FK",
    "odds_home": 1.73,
    "odds_draw": 3.80,
    "odds_away": 3.90
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Nosaby IF",
    "away_team": "IFK Trelleborg",
    "odds_home": 2.60,
    "odds_draw": 3.70,
    "odds_away": 2.25
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Osterlen FF",
    "away_team": "FK Karlskrona",
    "odds_home": 3.00,
    "odds_draw": 3.70,
    "odds_away": 2.00
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Rappe GOIF",
    "away_team": "Staffenstorp Unit...",
    "odds_home": 2.40,
    "odds_draw": 3.50,
    "odds_away": 2.55
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Sweden - Division 2",
    "home_team": "Solvesborgs GoIF",
    "away_team": "Oskarshamns AIK",
    "odds_home": 2.90,
    "odds_draw": 3.60,
    "odds_away": 2.10
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Brazil - Brasileiro Serie C",
    "home_team": "AA Internacional ...",
    "away_team": "Maringa FC",
    "odds_home": 2.30,
    "odds_draw": 3.10,
    "odds_away": 3.00
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Russia - 2. Liga, Division B, Group 3",
    "home_team": "FC Rubin Yalta",
    "away_team": "FC Nart Cherkessk",
    "odds_home": 2.30,
    "odds_draw": 3.20,
    "odds_away": 2.60
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Russia - 2. Liga, Division B, Group 3",
    "home_team": "FC Sevastopol",
    "away_team": "FK Angusht Nazran",
    "odds_home": 1.15,
    "odds_draw": 5.60,
    "odds_away": 12.00
  },
  {
    "time": "27 Jun, 15:00",
    "league": "Russia - 2. Liga, Division B, Group 3",
    "home_team": "FC Kiziltash Ba...",
    "away_team": "FC Druzhba May...",
    "odds_home": 2.35,
    "odds_draw": 3.50,
    "odds_away": 2.40
  }
]

_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

def _parse_kickoff(time_str: str, year: int = 2026) -> datetime:
    # Format: "26 Jun, 12:30"
    parts = time_str.split(",")
    date_part = parts[0].strip().split()
    day = int(date_part[0])
    month = _MONTH_MAP[date_part[1]]

    time_part = parts[1].strip().split(":")
    hour = int(time_part[0])
    minute = int(time_part[1])

    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

def _make_fingerprint(kickoff: datetime, home: str, away: str, league: str) -> str:
    raw = f"{kickoff.date()}::{home.lower().strip()}::{away.lower().strip()}::{league.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()

async def seed():
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        for f in FIXTURES:
            if not f.get("home_team") or not f.get("away_team") or not f.get("league"):
                print(f"[warn] Skipping incomplete fixture: {f}")
                skipped += 1
                continue

            try:
                kickoff = _parse_kickoff(f["time"])
            except Exception as e:
                print(f"[warn] Date parse error for {f}: {e}")
                skipped += 1
                continue

            home = f["home_team"].strip()
            away = f["away_team"].strip()
            league = f["league"].strip()
            fp = _make_fingerprint(kickoff, home, away, league)

            # Check if exists
            existing = await db.execute(select(Match).where(Match.fingerprint == fp))
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            match = Match(
                home_team=home,
                away_team=away,
                league=league,
                kickoff_time=kickoff,
                status="scheduled",
                source="manual_upload",
                fingerprint=fp,
                market_type="sports",
                opening_odds_home=f.get("odds_home"),
                opening_odds_draw=f.get("odds_draw"),
                opening_odds_away=f.get("odds_away"),
            )
            db.add(match)
            inserted += 1

        await db.commit()
    print(f"Done. Inserted: {inserted}, Skipped: {skipped}")

if __name__ == "__main__":
    asyncio.run(seed())
