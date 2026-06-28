from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, RecyclingRule, ScanFeedback, ScanRecord


load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def get_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///ecolens.db"))


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


DEMO_RULES = [
    {
        "item_name": "寶特瓶",
        "category": "資源回收 / 塑膠類",
        "material": "PET 1 號塑膠",
        "disposal_steps": "倒空內容物，簡單沖洗，瓶身壓扁，瓶蓋與瓶身可一起投入塑膠容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://pet-bottle",
        "keywords": "PET,寶特瓶,塑膠瓶,飲料瓶",
    },
    {
        "item_name": "鋁箔包",
        "category": "資源回收 / 紙容器",
        "material": "紙、塑膠膜、鋁箔複合材",
        "disposal_steps": "喝完後壓扁，若有吸管與塑膠套需分開處理，依地方規定投入紙容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://carton",
        "keywords": "鋁箔包,紙容器,飲料盒,牛奶盒",
    },
    {
        "item_name": "手搖飲塑膠杯",
        "category": "資源回收 / 塑膠杯",
        "material": "PP 或 PET 塑膠",
        "disposal_steps": "倒掉剩餘飲料，杯膜與吸管分開，杯身沖洗後投入塑膠類回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://drink-cup",
        "keywords": "手搖飲,塑膠杯,PP,PET,飲料杯",
    },
    {
        "item_name": "紙餐盒",
        "category": "依污染程度判斷",
        "material": "紙類或淋膜紙",
        "disposal_steps": "若油污嚴重通常不適合回收；若乾淨且地方接受紙容器回收，可清空後回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://paper-box",
        "keywords": "紙餐盒,便當盒,外送盒,紙容器",
    },
    {
        "item_name": "紙箱",
        "category": "資源回收 / 廢紙類",
        "material": "瓦楞紙板",
        "disposal_steps": "先移除膠帶、塑膠包材與非紙類填充物，保持乾燥並壓平後投入廢紙類回收；若受潮、沾油或沾滿食物殘渣，通常不適合回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://cardboard-box",
        "keywords": "紙箱,瓦楞紙箱,紙板,棕色紙箱,包裹箱,外箱,cardboard,carton box,brown box",
    },
    {
        "item_name": "鐵鋁罐",
        "category": "資源回收 / 金屬類",
        "material": "鋁或鐵",
        "disposal_steps": "倒空內容物，簡單沖洗，壓扁後投入金屬容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://can",
        "keywords": "鐵罐,鋁罐,易開罐,金屬",
    },
    {
        "item_name": "電池",
        "category": "資源回收 / 乾電池",
        "material": "金屬與化學材料",
        "disposal_steps": "不可丟一般垃圾，應集中後投入超商、量販店或清潔隊提供的電池回收點。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://battery",
        "keywords": "電池,乾電池,鈕扣電池,回收點",
    },
    {
        "item_name": "玻璃瓶",
        "category": "資源回收 / 玻璃類",
        "material": "玻璃",
        "disposal_steps": "倒空內容物，簡單沖洗，避免破裂割傷，依地方規定投入玻璃容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://glass-bottle",
        "keywords": "玻璃瓶,玻璃罐,酒瓶,醬料瓶",
    },
    {
        "item_name": "塑膠袋",
        "category": "依地方規定回收",
        "material": "PE 或塑膠薄膜",
        "disposal_steps": "乾淨塑膠袋可集中回收；若沾滿油污、湯汁或食物殘渣，通常應作一般垃圾處理。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://plastic-bag",
        "keywords": "塑膠袋,PE,塑膠薄膜,購物袋",
    },
    {
        "item_name": "保麗龍餐盒",
        "category": "依地方規定回收",
        "material": "PS 保麗龍",
        "disposal_steps": "乾淨保麗龍可依地方規定回收；若沾油或食物殘渣，需先清潔，無法清潔時作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://styrofoam-box",
        "keywords": "保麗龍,PS,保麗龍餐盒,泡棉",
    },
    {
        "item_name": "廚餘",
        "category": "廚餘",
        "material": "食物殘渣",
        "disposal_steps": "瀝乾水分後投入廚餘桶；骨頭、貝殼、衛生紙等不可混入，依地方規定分類生熟廚餘。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://food-waste",
        "keywords": "廚餘,食物殘渣,剩菜,果皮",
    },
    {
        "item_name": "衛生紙",
        "category": "一般垃圾",
        "material": "污染紙類",
        "disposal_steps": "使用過的衛生紙、紙巾、面紙、擦手紙或濕紙巾多屬一般垃圾，不建議投入紙類回收。外包裝若標示可丟馬桶的衛生紙，才可少量投入馬桶。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://tissue",
        "keywords": "衛生紙,紙巾,面紙,餐巾紙,擦手紙,廚房紙巾,濕紙巾,紙尿布,污染紙類,一般垃圾,tissue,toilet paper",
    },
    {
        "item_name": "口罩",
        "category": "一般垃圾",
        "material": "不織布與複合材",
        "disposal_steps": "口罩屬個人衛生用品，使用後請包好並投入一般垃圾，不要投入資源回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://mask",
        "keywords": "口罩,醫療口罩,外科口罩,不織布口罩,mask",
    },
    {
        "item_name": "陶瓷與非容器玻璃",
        "category": "一般垃圾",
        "material": "陶瓷、耐熱玻璃或非容器玻璃",
        "disposal_steps": "陶瓷碗盤、馬克杯、玻璃杯、鏡子等通常不能當玻璃容器回收；破裂時請包好避免割傷，再依地方規定作一般垃圾或交清潔隊。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://ceramic-glassware",
        "keywords": "陶瓷,陶瓷碗,陶瓷盤,碗盤,馬克杯,玻璃杯,玻璃碗,鏡子,ceramic,mug",
    },
    {
        "item_name": "筷子與小型餐具",
        "category": "一般垃圾",
        "material": "竹木、塑膠或複合材",
        "disposal_steps": "免洗筷、竹筷、塑膠吸管與小型餐具體積小且常有污染，通常作一般垃圾；乾淨可回收餐具仍請依地方公告處理。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://small-utensils",
        "keywords": "筷子,免洗筷,竹筷,木筷,塑膠吸管,吸管,湯匙,叉子,餐具,straw,chopsticks",
    },
    {
        "item_name": "乾淨舊衣物",
        "category": "資源回收 / 舊衣類",
        "material": "布料、紡織品",
        "disposal_steps": "乾淨且可再利用的衣服可投入舊衣回收；破損、發臭、泡水或嚴重髒污的衣物通常不具回收價值，請作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://clothes",
        "keywords": "衣服,舊衣,外套,褲子,裙子,T恤,襯衫,布料,clothes,shirt",
    },
    {
        "item_name": "鞋類",
        "category": "依地方規定回收",
        "material": "橡膠、皮革、布料或複合材",
        "disposal_steps": "鞋子材質複合，各縣市規定不同；乾淨可再利用者可找舊鞋回收或捐贈，破損髒污者多作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://shoes",
        "keywords": "鞋子,球鞋,拖鞋,雨鞋,皮鞋,舊鞋,鞋類,shoes",
    },
    {
        "item_name": "牙刷與牙膏軟管",
        "category": "一般垃圾",
        "material": "塑膠、橡膠或複合軟管",
        "disposal_steps": "牙刷、牙膏軟管、修正液瓶等小型複合塑膠多不適合回收，通常作一般垃圾；外包裝紙盒可乾淨攤平後回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://toothbrush-tube",
        "keywords": "牙刷,牙膏,牙膏管,刷子,修正液瓶,toothbrush,toothpaste",
    },
    {
        "item_name": "雨傘",
        "category": "依地方規定回收",
        "material": "金屬、塑膠、布料複合材",
        "disposal_steps": "雨傘由金屬骨架、塑膠與布料組成，能拆解時可分開回收金屬，無法拆解時請依地方規定交清潔隊或作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://umbrella",
        "keywords": "雨傘,折傘,傘骨,陽傘,umbrella",
    },
    {
        "item_name": "照明光源",
        "category": "資源回收 / 照明光源",
        "material": "玻璃、金屬與電子材料",
        "disposal_steps": "燈泡、燈管、省電燈泡與 LED 燈請避免打破，集中後交給清潔隊、回收車或指定回收點。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://lighting",
        "keywords": "燈泡,燈管,日光燈,省電燈泡,LED燈,照明光源,light bulb,lamp",
    },
    {
        "item_name": "小型電子與線材",
        "category": "依地方規定回收 / 小家電與3C",
        "material": "金屬、塑膠、電路板與線材",
        "disposal_steps": "充電線、耳機、手機、滑鼠、鍵盤等可依地方規定交資源回收車、3C回收點或清潔隊；含電池者請勿丟一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://small-electronics",
        "keywords": "充電線,電線,傳輸線,耳機,手機,滑鼠,鍵盤,隨身碟,行動電源,小家電,3C,charger,cable,earphone,phone",
    },
    {
        "item_name": "藥品包裝",
        "category": "依材質判斷",
        "material": "紙盒、塑膠瓶或鋁塑複合包材",
        "disposal_steps": "過期或未用完藥品可詢問藥局或醫療院所；乾淨外紙盒可回收，鋁塑泡殼、藥袋或受污染包裝多作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://medicine-packaging",
        "keywords": "藥品包裝,藥袋,藥盒,藥罐,鋁箔藥包,泡殼包裝,過期藥,medicine,blister pack",
    },
    {
        "item_name": "塑膠薄膜與泡泡紙",
        "category": "一般垃圾",
        "material": "塑膠薄膜或複合膜",
        "disposal_steps": "泡泡紙、保鮮膜、膠帶、塑膠繩等薄膜類或複合材通常不適合回收；若地方有乾淨塑膠膜回收規定，請依公告處理。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://plastic-film",
        "keywords": "泡泡紙,氣泡紙,泡泡袋,保鮮膜,塑膠膜,膠帶,塑膠繩,包裝膜,bubble wrap,plastic wrap",
    },
    {
        "item_name": "外送紙袋",
        "category": "資源回收 / 廢紙類",
        "material": "紙類",
        "disposal_steps": "乾淨紙袋可攤平後投入廢紙類回收；若沾油、沾湯汁或有食物殘渣，通常不適合回收，請作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://paper-bag",
        "keywords": "紙袋,外送紙袋,牛皮紙袋,購物紙袋,飲料杯套,紙杯套,paper bag",
    },
    {
        "item_name": "廢食用油",
        "category": "依地方規定回收 / 廢油",
        "material": "食用油",
        "disposal_steps": "廢食用油不可倒入水槽或馬桶，請裝瓶密封後依地方規定交清潔隊或指定回收管道。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://used-cooking-oil",
        "keywords": "廢油,食用油,炸油,回鍋油,油脂,used cooking oil",
    },
    {
        "item_name": "骨頭與貝殼",
        "category": "一般垃圾",
        "material": "硬質食物殘渣",
        "disposal_steps": "骨頭、貝殼、蟹殼、蛋殼等硬質殘渣不一定適合廚餘回收，請依地方規定；不確定時瀝乾後作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://bones-shells",
        "keywords": "骨頭,雞骨,魚骨,豬骨,貝殼,蟹殼,蝦殼,蛋殼,bone,shell",
    },
    {
        "item_name": "水果網套",
        "category": "依地方規定回收",
        "material": "發泡塑膠或保麗龍緩衝材",
        "disposal_steps": "乾淨水果網套、保麗龍緩衝材部分地區可回收；若髒污、破碎或地方不收，請作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://fruit-foam-net",
        "keywords": "水果網套,水果套,泡棉網,保麗龍網,緩衝網,發泡網,foam net",
    },
]


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if seed:
        seed_demo_data()


def seed_demo_data() -> None:
    with SessionLocal() as session:
        for item in DEMO_RULES:
            upsert_rule(session, item)
        session.commit()


def upsert_rule(session: Session, rule_data: dict[str, object]) -> bool:
    item_name = str(rule_data["item_name"])
    city = str(rule_data.get("city", "通用"))
    existing = session.scalar(
        select(RecyclingRule).where(
            RecyclingRule.item_name == item_name,
            RecyclingRule.city == city,
        )
    )
    if existing:
        existing.category = str(rule_data.get("category", existing.category))
        existing.material = str(rule_data.get("material", existing.material))
        existing.disposal_steps = str(rule_data.get("disposal_steps", existing.disposal_steps))
        existing.source_name = str(rule_data.get("source_name", existing.source_name))
        existing.source_url = str(rule_data.get("source_url", existing.source_url))
        existing.keywords = str(rule_data.get("keywords", existing.keywords))
        return False

    session.add(RecyclingRule(**rule_data))
    return True


def save_scan_record(
    input_text: str,
    guessed_item: str,
    suggested_category: str,
    confidence: float,
    notes: str,
    device_type: str = "browser camera",
) -> ScanRecord:
    with SessionLocal() as session:
        record = ScanRecord(
            input_text=input_text,
            guessed_item=guessed_item,
            suggested_category=suggested_category,
            confidence=confidence,
            notes=notes,
            device_type=device_type,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def save_scan_feedback(
    scan_id: int,
    is_correct: bool,
    corrected_item: str = "",
    corrected_category: str = "",
    user_note: str = "",
) -> ScanFeedback:
    with SessionLocal() as session:
        record = session.get(ScanRecord, scan_id)
        if record is None:
            raise ValueError("Scan record not found.")

        feedback = ScanFeedback(
            scan_id=scan_id,
            is_correct=is_correct,
            corrected_item=corrected_item,
            corrected_category=corrected_category,
            user_note=user_note,
        )
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        return feedback
