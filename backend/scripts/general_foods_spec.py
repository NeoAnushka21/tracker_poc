"""The curated general food list: our own short names, aliases (incl. Indian names) and piece
sizes, each pointing at one USDA SR Legacy food for its numbers (per 100 g).

- F(name, usda description, *aliases, piece=...) adds one food. `piece` is grams in one piece,
  or a USDA portion name ("medium", "large") to read it from the data.
- P(name, raw description, cooked description, *aliases) adds a raw/cooked pair for foods whose
  calories per 100 g change a lot when cooked (meat, fish, rice, grains, dals). For those the
  app always asks "raw or cooked?" unless the user said it.

Aliases are ours (typed names), not USDA's. Keep names short and the way people type them.
Run build_general_foods.py after editing.
"""
FOODS: list[dict] = []


def F(name: str, usda: str, *aliases: str, piece: float | str | None = None, state: str | None = None) -> None:
    FOODS.append({"name": name, "usda": usda, "aliases": list(aliases), "piece": piece, "state": state})


def P(name: str, raw: str, cooked: str, *aliases: str, piece: float | None = None) -> None:
    F(name, raw, *aliases, piece=piece, state="raw")
    F(name, cooked, *aliases, piece=piece, state="cooked")


# --- fruits ------------------------------------------------------------------------------
F("apple", "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)", "seb", "saib", piece="medium")
F("banana", "Bananas, raw", "kela", piece="medium")
F("mango", "Mangos, raw", "aam", piece=336)
F("orange", "Oranges, raw, all commercial varieties", "santra", "narangi", piece=131)
F("papaya", "Papayas, raw", "papita")
F("pineapple", "Pineapple, raw, all varieties", "ananas")
F("watermelon", "Watermelon, raw", "tarbooj", "tarbuj")
F("muskmelon", "Melons, cantaloupe, raw", "cantaloupe", "kharbooja", "kharbuja")
F("grapes", "Grapes, red or green (European type, such as Thompson seedless), raw", "angoor", "grape", piece=5)
F("guava", "Guavas, common, raw", "amrood", "amrud", "peru", piece=55)
F("pomegranate", "Pomegranates, raw", "anar", piece=282)
F("pear", "Pears, raw", "nashpati", piece=178)
F("peach", "Peaches, yellow, raw", "aadu", piece=150)
F("plum", "Plums, raw", "aloo bukhara", piece=66)
F("kiwi", "Kiwifruit, green, raw", "kiwifruit", piece=69)
F("strawberries", "Strawberries, raw", "strawberry", piece=12)
F("blueberries", "Blueberries, raw", "blueberry")
F("raspberries", "Raspberries, raw", "raspberry")
F("blackberries", "Blackberries, raw", "blackberry")
F("cherries", "Cherries, sweet, raw", "cherry", piece=8)
F("lychee", "Litchis, raw", "litchi", "lichi", piece=10)
F("custard apple", "Sugar-apples, (sweetsop), raw", "sitaphal", "sugar apple", "sharifa")
F("jackfruit", "Jackfruit, raw", "kathal", "fanas")
F("chikoo", "Sapodilla, raw", "chiku", "sapota", "sapodilla", piece=170)
F("jamun", "Java-plum, (jambolan), raw", "java plum", "jambolan", piece=3)
F("star fruit", "Carambola, (starfruit), raw", "carambola", "kamrakh", piece=91)
F("dates", "Dates, medjool", "khajoor", "khajur", "date", piece=24)
F("figs", "Figs, raw", "anjeer", "fig", piece=50)
F("dried figs", "Figs, dried, uncooked", "dry anjeer", "dried fig", piece=8)
F("raisins", "Raisins, dark, seedless (Includes foods for USDA's Food Distribution Program)", "kishmish", "raisin")
F("dried apricots", "Apricots, dried, sulfured, uncooked", "dry apricot", "khubani")
F("prunes", "Plums, dried (prunes), uncooked", "prune")
F("apricot", "Apricots, raw", "apricots", piece=35)
F("avocado", "Avocados, raw, all commercial varieties", "butter fruit", piece=150)
F("coconut", "Nuts, coconut meat, raw", "nariyal", "fresh coconut", "coconut meat")
F("lemon", "Lemons, raw, without peel", "nimbu", "lime", piece=58)
F("lemon juice", "Lemon juice, raw", "nimbu juice")
F("tangerine", "Tangerines, (mandarin oranges), raw", "mandarin", "kinnow", piece=88)
F("grapefruit", "Grapefruit, raw, pink and red, all areas")
F("passion fruit", "Passion-fruit, (granadilla), purple, raw", "passionfruit", piece=18)
F("persimmon", "Persimmons, japanese, raw", piece=168)
F("tamarind", "Tamarinds, raw", "imli")
F("plantain", "Plantains, yellow, raw", "raw banana", "kacha kela")
F("cranberries, dried", "Cranberries, dried, sweetened (Includes foods for USDA's Food Distribution Program)", "dried cranberries", "craisins")

# --- vegetables ----------------------------------------------------------------------------
F("onion", "Onions, raw", "pyaz", "pyaaz", "kanda", "onions", piece=110)
F("tomato", "Tomatoes, red, ripe, raw, year round average", "tamatar", "tomatoes", piece=123)
F("potato", "Potatoes, flesh and skin, raw", "aloo", "alu", "potatoes", piece=213)
F("boiled potato", "Potatoes, boiled, cooked without skin, flesh, without salt", "boiled aloo", piece=136)
F("sweet potato", "Sweet potato, raw, unprepared (Includes foods for USDA's Food Distribution Program)", "shakarkandi", piece=130)
F("carrot", "Carrots, raw", "gajar", "carrots", piece=61)
F("cucumber", "Cucumber, with peel, raw", "kheera", "kakdi", piece=300)
F("spinach", "Spinach, raw", "palak")
F("cabbage", "Cabbage, raw", "patta gobi", "band gobi")
F("cauliflower", "Cauliflower, raw", "gobi", "phool gobi", "gobhi")
F("broccoli", "Broccoli, raw")
F("green capsicum", "Peppers, sweet, green, raw", "capsicum", "shimla mirch", "green pepper", "bell pepper", piece=119)
F("red capsicum", "Peppers, sweet, red, raw", "red bell pepper", "red pepper", piece=119)
F("yellow capsicum", "Peppers, sweet, yellow, raw", "yellow bell pepper", piece=186)
F("green peas", "Peas, green, raw", "matar", "peas", "hara matar")
F("frozen peas", "Peas, green, frozen, unprepared (Includes foods for USDA's Food Distribution Program)")
F("sweet corn", "Corn, sweet, yellow, raw", "corn", "makka", "bhutta", "makai")
F("okra", "Okra, raw", "bhindi", "lady finger", "ladies finger")
F("brinjal", "Eggplant, raw", "baingan", "eggplant", "aubergine")
F("bottle gourd", "Gourd, white-flowered (calabash), raw", "lauki", "dudhi", "ghiya")
F("bitter gourd", "Balsam-pear (bitter gourd), pods, raw", "karela")
F("ridge gourd", "Gourd, dishcloth (towelgourd), raw", "turai", "tori", "luffa")
F("pumpkin", "Pumpkin, raw", "kaddu", "sitaphal kaddu")
F("beetroot", "Beets, raw", "beet", "chukandar", piece=82)
F("radish", "Radishes, raw", "mooli", "muli")
F("turnip", "Turnips, raw", "shalgam")
F("green beans", "Beans, snap, green, raw", "french beans", "beans", "farasbi")
F("mushrooms", "Mushrooms, white, raw", "mushroom", "khumbi")
F("lettuce", "Lettuce, iceberg (includes crisphead types), raw", "iceberg")
F("kale", "Kale, raw")
F("coriander leaves", "Coriander (cilantro) leaves, raw", "dhania", "cilantro", "hara dhania")
F("mint leaves", "Spearmint, fresh", "pudina", "mint")
F("garlic", "Garlic, raw", "lehsun", "lasun", piece=3)
F("ginger", "Ginger root, raw", "adrak")
F("green chilli", "Peppers, hot chili, green, raw", "hari mirch", "green chili", "chilli", piece=45)
F("spring onion", "Onions, spring or scallions (includes tops and bulb), raw", "scallion", "hara pyaz")
F("celery", "Celery, raw")
F("zucchini", "Squash, summer, zucchini, includes skin, raw", "courgette")
F("drumstick", "Drumstick pods, raw", "moringa", "saijan", "shevga")
F("drumstick leaves", "Drumstick leaves, raw", "moringa leaves")
F("colocasia", "Taro, raw", "arbi", "taro")
F("yam", "Yam, raw", "suran", "jimikand")
F("lotus root", "Lotus root, raw", "kamal kakdi", "bhein")
F("amaranth leaves", "Amaranth leaves, raw", "chaulai", "rajgira leaves")
F("mustard greens", "Mustard greens, raw", "sarson", "sarson ka saag")
F("fenugreek seeds", "Spices, fenugreek seed", "methi dana", "methi seeds")
F("leek", "Leeks, (bulb and lower leaf-portion), raw", "leeks")
F("asparagus", "Asparagus, raw")
F("bean sprouts", "Mung beans, mature seeds, sprouted, raw", "sprouts", "moong sprouts", "sprouted moong")
F("baby corn", "Corn, sweet, white, raw")
F("red cabbage", "Cabbage, red, raw")
F("brussels sprouts", "Brussels sprouts, raw")
F("jalapeno", "Peppers, jalapeno, raw", piece=14)
F("olives", "Olives, ripe, canned (small-extra large)", "olive", piece=4)

# --- grains, flours, breads -------------------------------------------------------------------
P("white rice", "Rice, white, long-grain, regular, raw, enriched", "Rice, white, long-grain, regular, enriched, cooked",
  "rice", "chawal", "basmati rice", "basmati", "steamed rice", "plain rice")
P("brown rice", "Rice, brown, long-grain, raw (Includes foods for USDA's Food Distribution Program)",
  "Rice, brown, long-grain, cooked (Includes foods for USDA's Food Distribution Program)")
P("oats", "Cereals, oats, regular and quick, not fortified, dry",
  "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt",
  "oatmeal", "rolled oats", "porridge")
P("quinoa", "Quinoa, uncooked", "Quinoa, cooked")
P("millet", "Millet, raw", "Millet, cooked", "bajra", "pearl millet")
P("barley", "Barley, pearled, raw", "Barley, pearled, cooked", "jau")
P("broken wheat", "Bulgur, dry", "Bulgur, cooked", "dalia", "daliya", "bulgur")
P("pasta", "Pasta, dry, enriched", "Pasta, cooked, enriched, without added salt",
  "macaroni", "spaghetti", "penne")
P("egg noodles", "Noodles, egg, dry, enriched", "Noodles, egg, enriched, cooked", "noodles")
P("soba noodles", "Noodles, japanese, soba, dry", "Noodles, japanese, soba, cooked", "soba")
F("whole wheat flour", "Wheat flour, whole-grain (Includes foods for USDA's Food Distribution Program)", "atta", "wheat flour", "gehun ka atta")
F("all purpose flour", "Wheat flour, white, all-purpose, enriched, bleached", "maida", "refined flour", "plain flour")
F("gram flour", "Chickpea flour (besan)", "besan", "chickpea flour")
F("rice flour", "Rice flour, white, unenriched", "chawal ka atta")
F("semolina", "Semolina, enriched", "sooji", "suji", "rava", "rawa")
F("jowar", "Sorghum grain", "sorghum", "jowar flour")
F("millet flour", "Millet flour", "bajra atta", "bajra flour")
F("cornmeal", "Cornmeal, whole-grain, yellow", "makki ka atta", "maize flour", "corn flour")
F("puffed rice", "Cereals ready-to-eat, rice, puffed, fortified", "murmura", "kurmura", "mamra")
F("popcorn", "Snacks, popcorn, air-popped", "air popped popcorn")
F("roti", "Bread, chapati or roti, whole wheat, commercially prepared, frozen", "chapati", "chapatti", "phulka", "rotis", piece=40)
F("plain roti", "Bread, chapati or roti, plain, commercially prepared", piece=40)
F("naan", "Bread, naan, plain, commercially prepared, refrigerated", "nan", piece=90)
F("paratha", "Bread, paratha, whole wheat, commercially prepared, frozen", "parantha", "plain paratha", piece=80)
F("white bread", "Bread, white, commercially prepared (includes soft bread crumbs)", "bread", "bread slice", piece=25)
F("brown bread", "Bread, whole-wheat, commercially prepared", "whole wheat bread", "wheat bread", piece=32)
F("multigrain bread", "Bread, multi-grain (includes whole-grain)", "multi grain bread", piece=26)
F("pita", "Bread, pita, white, enriched", "pita bread", piece=60)
F("tortilla", "Tortillas, ready-to-bake or -fry, flour, refrigerated", "wrap", "flour tortilla", piece=49)
F("corn flakes", "Cereals ready-to-eat, RALSTON Corn Flakes", "cornflakes")
F("granola", "Cereals ready-to-eat, granola, homemade")
F("rice cake", "Snacks, rice cakes, brown rice, plain, unsalted", "rice cakes", piece=9)
F("crackers", "Crackers, saltines (includes oyster, soda, soup)", "saltines", piece=3)
F("digestive biscuit", "Cookies, graham crackers, plain or honey (includes cinnamon)", "biscuit", "biscuits", "digestive", piece=15)

# --- dals, beans, soy --------------------------------------------------------------------------
P("lentils", "Lentils, raw", "Lentils, mature seeds, cooked, boiled, without salt",
  "masoor", "masoor dal", "dal", "daal", "lentil")
P("toor dal", "Pigeon peas (red gram), mature seeds, raw", "Pigeon peas (red gram), mature seeds, cooked, boiled, without salt",
  "arhar dal", "tur dal", "tuvar dal", "pigeon peas", "arhar")
P("moong dal", "Mung beans, mature seeds, raw", "Mung beans, mature seeds, cooked, boiled, without salt",
  "moong", "mung", "mung beans", "green gram", "mung dal", "moong beans")
P("urad dal", "Mungo beans, mature seeds, raw", "Mungo beans, mature seeds, cooked, boiled, without salt",
  "urad", "black gram", "udad dal")
P("chickpeas", "Chickpeas (garbanzo beans, bengal gram), mature seeds, raw",
  "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt",
  "chana", "chole", "kabuli chana", "kala chana", "chana dal", "garbanzo", "chickpea")
P("kidney beans", "Beans, kidney, all types, mature seeds, raw",
  "Beans, kidney, all types, mature seeds, cooked, boiled, without salt", "rajma")
P("black eyed peas", "Cowpeas, common (blackeyes, crowder, southern), mature seeds, raw",
  "Cowpeas, common (blackeyes, crowder, southern), mature seeds, cooked, boiled, without salt",
  "lobia", "chawli", "cowpeas", "black eyed beans")
P("black beans", "Beans, black, mature seeds, raw", "Beans, black, mature seeds, cooked, boiled, without salt")
P("moth beans", "Mothbeans, mature seeds, raw", "Mothbeans, mature seeds, cooked, boiled, without salt", "matki", "moth")
P("soybeans", "Soybeans, mature seeds, raw", "Soybeans, mature cooked, boiled, without salt", "soybean", "soya bean")
P("split peas", "Peas, green, split, mature seeds, raw", "Peas, split, mature seeds, cooked, boiled, without salt",
  "dried peas", "safed matar", "white peas")
F("tofu", "Tofu, raw, firm, prepared with calcium sulfate", "firm tofu", "soya paneer")
F("soy milk", "Soymilk, original and vanilla, unfortified", "soya milk", "soymilk")
F("peanuts", "Peanuts, all types, raw", "moongfali", "mungfali", "groundnuts", "peanut")
F("roasted peanuts", "Peanuts, all types, dry-roasted, without salt", "roasted moongfali")
F("hummus", "Hummus, commercial", "houmous")

# --- dairy -------------------------------------------------------------------------------------
F("milk", "Milk, whole, 3.25% milkfat, with added vitamin D", "whole milk", "full cream milk", "doodh", "dudh", "full fat milk")
F("toned milk", "Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and vitamin D", "2% milk", "low fat milk")
F("double toned milk", "Milk, lowfat, fluid, 1% milkfat, with added vitamin A and vitamin D", "1% milk")
F("skim milk", "Milk, nonfat, fluid, with added vitamin A and vitamin D (fat free or skim)", "skimmed milk", "fat free milk")
F("buffalo milk", "Milk, indian buffalo, fluid", "bhains ka doodh")
F("goat milk", "Milk, goat, fluid, with added vitamin D", "bakri ka doodh")
F("curd", "Yogurt, plain, whole milk", "dahi", "yogurt", "yoghurt", "plain yogurt")
F("low fat curd", "Yogurt, plain, low fat", "low fat yogurt", "low fat dahi")
F("greek yogurt", "Yogurt, Greek, plain, nonfat (Includes foods for USDA's Food Distribution Program)", "hung curd", "greek yoghurt")
F("buttermilk", "Milk, buttermilk, fluid, cultured, lowfat", "chaas", "chhach", "mattha")
F("cheddar cheese", "Cheese, cheddar (Includes foods for USDA's Food Distribution Program)", "cheddar", "cheese")
F("mozzarella", "Cheese, mozzarella, whole milk", "mozzarella cheese", "pizza cheese")
F("processed cheese", "Cheese, pasteurized process, American, fortified with vitamin D", "cheese slice", "amul cheese", piece=21)
F("cottage cheese", "Cheese, cottage, creamed, large or small curd")
F("cream cheese", "Cheese, cream")
F("parmesan", "Cheese, parmesan, grated", "parmesan cheese")
F("feta", "Cheese, feta", "feta cheese")
F("butter", "Butter, salted", "makhan", "makkhan", "salted butter")
F("unsalted butter", "Butter, without salt", "white butter", "safed makhan")
F("ghee", "Butter oil, anhydrous", "desi ghee", "clarified butter")
F("fresh cream", "Cream, fluid, heavy whipping", "cream", "malai", "heavy cream")
F("sour cream", "Cream, sour, cultured")
F("condensed milk", "Milk, canned, condensed, sweetened", "milkmaid")
F("milk powder", "Milk, dry, whole, with added vitamin D", "whole milk powder")
F("skim milk powder", "Milk, dry, nonfat, regular, without added vitamin A and vitamin D", "smp")
F("vanilla ice cream", "Ice creams, vanilla", "ice cream")

# --- eggs --------------------------------------------------------------------------------------
F("egg", "Egg, whole, raw, fresh", "eggs", "whole egg", "anda", "ande", "raw egg", piece="large")
F("boiled egg", "Egg, whole, cooked, hard-boiled", "hard boiled egg", "boiled eggs", "ubla anda", piece="large")
F("egg white", "Egg, white, raw, fresh", "egg whites", piece="large")
F("egg yolk", "Egg, yolk, raw, fresh", "egg yolks", piece="large")
F("omelette", "Egg, whole, cooked, omelet", "omelet")
F("fried egg", "Egg, whole, cooked, fried", "fried eggs", "sunny side up", piece="large")
F("scrambled eggs", "Egg, whole, cooked, scrambled", "scrambled egg", "bhurji", "egg bhurji")
F("poached egg", "Egg, whole, cooked, poached", "poached eggs", piece="large")

# --- meat and fish (raw/cooked pairs; "cooked" = plain roasted/grilled/steamed, no oil) -----------
P("chicken breast", "Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw",
  "Chicken, broilers or fryers, breast, meat only, cooked, roasted", "chicken breasts", "boneless chicken breast")
P("chicken thigh", "Chicken, broilers or fryers, dark meat, thigh, meat only, raw",
  "Chicken, broilers or fryers, thigh, meat only, cooked, roasted", "chicken thighs")
P("chicken drumstick", "Chicken, broilers or fryers, dark meat, drumstick, meat only, raw",
  "Chicken, broilers or fryers, dark meat, drumstick, meat only, cooked, roasted", "chicken leg")
P("chicken wings", "Chicken, broilers or fryers, wing, meat and skin, raw",
  "Chicken, broilers or fryers, wing, meat and skin, cooked, roasted", "chicken wing", "wings")
P("chicken", "Chicken, broilers or fryers, meat only, raw", "Chicken, broilers or fryers, meat only, cooked, roasted",
  "murgh", "murg", "chicken meat", "boneless chicken")
P("chicken mince", "Chicken, ground, raw", "Chicken, ground, crumbles, cooked, pan-browned", "ground chicken", "chicken keema")
P("mutton", "Game meat, goat, raw", "Game meat, goat, cooked, roasted", "goat meat", "goat", "gosht", "bakra")
P("lamb mince", "Lamb, ground, raw", "Lamb, ground, cooked, broiled", "ground lamb", "mutton keema", "keema", "lamb")
P("beef mince", "Beef, ground, 85% lean meat / 15% fat, raw (Includes foods for USDA's Food Distribution Program)",
  "Beef, ground, 85% lean meat / 15% fat, crumbles, cooked, pan-browned", "ground beef", "beef", "minced beef")
P("pork", "Pork, fresh, loin, tenderloin, separable lean only, raw",
  "Pork, fresh, loin, tenderloin, separable lean only, cooked, roasted", "pork tenderloin", "pork loin")
P("salmon", "Fish, salmon, Atlantic, farmed, raw", "Fish, salmon, Atlantic, farmed, cooked, dry heat")
P("tuna", "Fish, tuna, fresh, yellowfin, raw", "Fish, tuna, yellowfin, fresh, cooked, dry heat", "fresh tuna")
P("cod", "Fish, cod, Atlantic, raw", "Fish, cod, Atlantic, cooked, dry heat")
P("tilapia", "Fish, tilapia, raw", "Fish, tilapia, cooked, dry heat")
P("mackerel", "Fish, mackerel, Atlantic, raw", "Fish, mackerel, Atlantic, cooked, dry heat", "bangda", "bangude")
P("pomfret", "Fish, pompano, florida, raw", "Fish, pompano, florida, cooked, dry heat", "pompano", "paplet")
P("prawns", "Crustaceans, shrimp, raw", "Crustaceans, shrimp, cooked", "shrimp", "prawn", "jhinga", "kolambi")
P("turkey breast", "Turkey, whole, breast, meat only, raw", "Turkey, whole, breast, meat only, cooked, roasted", "turkey")
F("canned tuna", "Fish, tuna, light, canned in water, drained solids (Includes foods for USDA's Food Distribution Program)",
  "tuna in water", "tinned tuna", "tuna can")
F("sardines", "Fish, sardine, Atlantic, canned in oil, drained solids with bone", "canned sardines", "tinned sardines")
F("crab", "Crustaceans, crab, blue, cooked, moist heat", "crab meat", "kekda")
F("bacon", "Pork, cured, bacon, pre-sliced, cooked, pan-fried", piece=8)
F("ham", "Ham, sliced, regular (approximately 11% fat)", "ham slice", piece=28)
F("chicken sausage", "Sausage, chicken, beef, pork, skinless, smoked", "sausage", "sausages", piece=50)
F("chicken liver", "Chicken, liver, all classes, cooked, simmered", "kaleji", "liver")

# --- nuts and seeds -----------------------------------------------------------------------------
F("almonds", "Nuts, almonds", "badam", "almond", piece=1.2)
F("cashews", "Nuts, cashew nuts, raw", "kaju", "cashew", "cashew nuts", piece=1.5)
F("walnuts", "Nuts, walnuts, english", "akhrot", "walnut", piece=4)
F("pistachios", "Nuts, pistachio nuts, raw", "pista", "pistachio", piece=0.7)
F("hazelnuts", "Nuts, hazelnuts or filberts", "hazelnut")
F("pecans", "Nuts, pecans", "pecan")
F("macadamia", "Nuts, macadamia nuts, raw", "macadamia nuts")
F("brazil nuts", "Nuts, brazilnuts, dried, unblanched", "brazil nut", piece=5)
F("peanut butter", "Peanut butter, smooth style, without salt", "pb", "peanut butter smooth")
F("almond butter", "Nuts, almond butter, plain, without salt added")
F("flaxseeds", "Seeds, flaxseed", "alsi", "flax seeds", "flaxseed", "linseed")
F("chia seeds", "Seeds, chia seeds, dried", "chia", "sabja")
F("sunflower seeds", "Seeds, sunflower seed kernels, dried", "sunflower seed")
F("pumpkin seeds", "Seeds, pumpkin and squash seed kernels, dried", "pumpkin seed", "pepitas")
F("sesame seeds", "Seeds, sesame seeds, whole, dried", "til", "sesame")
F("makhana", "Seeds, lotus seeds, dried", "fox nuts", "foxnut", "lotus seeds", "phool makhana")
F("desiccated coconut", "Nuts, coconut meat, dried (desiccated), not sweetened", "dry coconut", "copra", "sukha nariyal")
F("watermelon seeds", "Seeds, watermelon seed kernels, dried", "magaz")
F("cumin seeds", "Spices, cumin seed", "jeera", "cumin")
F("mixed nuts", "Nuts, mixed nuts, dry roasted, with peanuts, without salt added", "dry fruits", "trail nuts")

# --- oils, fats, sweeteners, condiments -----------------------------------------------------------
F("olive oil", "Oil, olive, salad or cooking", "extra virgin olive oil", "evoo")
F("sunflower oil", "Oil, sunflower, linoleic (less than 60%)", "refined oil", "cooking oil", "oil", "vegetable oil")
F("mustard oil", "Oil, mustard", "sarson ka tel", "kachi ghani")
F("coconut oil", "Oil, coconut", "nariyal tel")
F("groundnut oil", "Oil, peanut, salad or cooking", "peanut oil", "moongfali tel")
F("soybean oil", "Oil, soybean, salad or cooking", "soya oil")
F("rice bran oil", "Oil, rice bran")
F("canola oil", "Oil, canola")
F("sesame oil", "Oil, sesame, salad or cooking", "til oil", "gingelly oil")
F("vanaspati", "Shortening, household, soybean (partially hydrogenated)-cottonseed (partially hydrogenated)", "dalda", "shortening")
F("mayonnaise", "Salad dressing, mayonnaise, regular", "mayo")
F("sugar", "Sugars, granulated", "cheeni", "chini", "white sugar")
F("brown sugar", "Sugars, brown")
F("honey", "Honey", "shahad", "madh")
F("maple syrup", "Syrups, maple")
F("jam", "Jams and preserves", "fruit jam")
F("dark chocolate", "Chocolate, dark, 70-85% cacao solids", "70% dark chocolate")
F("milk chocolate", "Candies, milk chocolate", "chocolate")
F("cocoa powder", "Cocoa, dry powder, unsweetened", "cocoa")
F("ketchup", "Catsup", "tomato ketchup", "tomato sauce")
F("soy sauce", "Soy sauce made from soy and wheat (shoyu)", "soya sauce")
F("mustard sauce", "Mustard, prepared, yellow", "mustard")
F("vinegar", "Vinegar, distilled", "white vinegar")
F("salsa", "Sauce, salsa, ready-to-serve")

# --- drinks ------------------------------------------------------------------------------------
F("black coffee", "Beverages, coffee, brewed, prepared with tap water", "coffee", "americano", "filter coffee decoction")
F("black tea", "Beverages, tea, black, brewed, prepared with tap water", "tea", "chai decoction", "green tea")
F("orange juice", "Orange juice, raw (Includes foods for USDA's Food Distribution Program)", "fresh orange juice", "santra juice")
F("apple juice", "Apple juice, canned or bottled, unsweetened, without added ascorbic acid")
F("coconut water", "Nuts, coconut water (liquid from coconuts)", "nariyal pani", "tender coconut water")
F("cola", "Beverages, carbonated, cola, regular", "coke", "pepsi", "soft drink")
F("almond milk", "Beverages, almond milk, unsweetened, shelf stable", "unsweetened almond milk")
F("beer", "Alcoholic beverage, beer, regular, all", "lager")
F("red wine", "Alcoholic beverage, wine, table, red", "wine")
F("whisky", "Alcoholic beverage, distilled, all (gin, rum, vodka, whiskey) 80 proof", "whiskey", "vodka", "rum", "gin")

# Not in SR Legacy in a usable form, so left to Saved Food / the AI for now: paneer, poha,
# jaggery, ragi, muesli, sugarcane juice, sweet lime (mosambi), amla, idli/dosa and other cooked dishes.
