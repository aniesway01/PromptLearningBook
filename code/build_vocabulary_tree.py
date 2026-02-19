# ATOM_TYPE: Type B
"""
建立樹狀提示詞辭典 JSON
用法: python build_vocabulary_tree.py
輸出: Doc/prompt_vocabulary_tree.json
"""
import sys
import io
import json
import sqlite3
import logging
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "uniform_map.db"
OUT_PATH = PROJECT_DIR / "Doc" / "prompt_vocabulary_tree.json"
LOG_PATH = PROJECT_DIR / "logs" / "build_vocabulary_tree.log"

(PROJECT_DIR / "logs").mkdir(exist_ok=True)
(PROJECT_DIR / "Doc").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("VocabTreeBuilder")

# ────────────────────────────────────────
# 樹狀結構定義（9 章 × 深度 2-3 層）
# 每個 term: {"en": str, "zh": str, "tip"?: str, "neg"?: bool, "lang"?: str}
# ────────────────────────────────────────

TREE = {
    "chapters": [
        {
            "id": "1", "title": "人物主體", "title_en": "Subject",
            "children": [
                {
                    "id": "1.1", "title": "人物基本",
                    "children": [
                        {
                            "id": "1.1.1", "title": "人數", "terms": [
                                {"en": "1girl", "zh": "單人女性"},
                                {"en": "solo", "zh": "單人"},
                                {"en": "1boy", "zh": "單人男性"},
                                {"en": "2girls", "zh": "兩人女性"},
                                {"en": "group", "zh": "群體"},
                                {"en": "couple", "zh": "情侶"},
                            ]
                        },
                        {
                            "id": "1.1.2", "title": "年齡", "terms": [
                                {"en": "teen", "zh": "青少年"},
                                {"en": "young adult", "zh": "年輕成人"},
                                {"en": "early 20s", "zh": "二十出頭"},
                                {"en": "student", "zh": "學生"},
                                {"en": "高校生くらいの女の子", "zh": "高中生年紀的女孩", "lang": "ja"},
                            ]
                        },
                        {
                            "id": "1.1.3", "title": "族裔", "terms": [
                                {"en": "japanese", "zh": "日本人"},
                                {"en": "korean", "zh": "韓國人"},
                                {"en": "east asian", "zh": "東亞人"},
                                {"en": "chinese", "zh": "中國人"},
                            ]
                        },
                        {
                            "id": "1.1.4", "title": "體型", "terms": [
                                {"en": "slim", "zh": "纖細"},
                                {"en": "petite", "zh": "嬌小"},
                                {"en": "athletic", "zh": "健美"},
                                {"en": "curvy", "zh": "豐滿"},
                                {"en": "slender", "zh": "修長"},
                                {"en": "tall", "zh": "高挑"},
                            ]
                        },
                    ]
                },
                {
                    "id": "1.2", "title": "臉部",
                    "children": [
                        {
                            "id": "1.2.1", "title": "臉型", "terms": [
                                {"en": "oval face", "zh": "鵝蛋臉"},
                                {"en": "V-line jaw", "zh": "V型下巴", "tip": "韓系常用"},
                                {"en": "delicate facial features", "zh": "精緻五官"},
                                {"en": "round face", "zh": "圓臉"},
                                {"en": "jawline", "zh": "下顎線"},
                            ]
                        },
                        {
                            "id": "1.2.2", "title": "膚質", "terms": [
                                {"en": "flawless skin", "zh": "無瑕肌膚"},
                                {"en": "glass skin", "zh": "玻璃肌", "tip": "韓系透亮質感"},
                                {"en": "dewy", "zh": "水潤感"},
                                {"en": "realistic skin texture", "zh": "真實皮膚紋理"},
                                {"en": "porcelain skin", "zh": "瓷肌"},
                            ]
                        },
                        {
                            "id": "1.2.3", "title": "膚色", "terms": [
                                {"en": "fair skin", "zh": "白皙膚色"},
                                {"en": "natural skin tone", "zh": "自然膚色"},
                                {"en": "peach-toned", "zh": "蜜桃色調"},
                                {"en": "tanned", "zh": "小麥色"},
                            ]
                        },
                        {
                            "id": "1.2.4", "title": "眼睛",
                            "children": [
                                {
                                    "id": "1.2.4a", "title": "眼型", "terms": [
                                        {"en": "big eyes", "zh": "大眼"},
                                        {"en": "almond eyes", "zh": "杏眼"},
                                        {"en": "droopy eyes", "zh": "下垂眼", "tip": "溫柔無辜感"},
                                        {"en": "narrow eyes", "zh": "細長眼"},
                                        {"en": "double eyelid", "zh": "雙眼皮"},
                                    ]
                                },
                                {
                                    "id": "1.2.4b", "title": "瞳色", "terms": [
                                        {"en": "brown eyes", "zh": "棕色瞳孔"},
                                        {"en": "blue eyes", "zh": "藍色瞳孔"},
                                        {"en": "green eyes", "zh": "綠色瞳孔"},
                                        {"en": "heterochromia", "zh": "異色瞳"},
                                        {"en": "dark eyes", "zh": "深色瞳孔"},
                                    ]
                                },
                                {
                                    "id": "1.2.4c", "title": "眼部描述", "terms": [
                                        {"en": "bright eyes", "zh": "明亮雙眼"},
                                        {"en": "glowing eyes", "zh": "發光雙眼"},
                                        {"en": "sparkling eyes", "zh": "閃亮雙眼"},
                                        {"en": "expressive eyes", "zh": "有神雙眼"},
                                    ]
                                },
                            ]
                        },
                        {
                            "id": "1.2.5", "title": "眉鼻唇", "terms": [
                                {"en": "natural brow", "zh": "自然眉型"},
                                {"en": "arched brow", "zh": "拱形眉"},
                                {"en": "small nose", "zh": "小鼻子"},
                                {"en": "button nose", "zh": "圓鼻頭"},
                                {"en": "glossy pink lips", "zh": "粉色光澤唇"},
                                {"en": "full lips", "zh": "豐唇"},
                                {"en": "thin lips", "zh": "薄唇"},
                                {"en": "cherry lips", "zh": "櫻桃小嘴"},
                            ]
                        },
                        {
                            "id": "1.2.6", "title": "妝容", "terms": [
                                {"en": "natural makeup", "zh": "自然妝"},
                                {"en": "light mascara", "zh": "淡睫毛膏"},
                                {"en": "subtle eyeliner", "zh": "淡眼線"},
                                {"en": "blush", "zh": "腮紅"},
                                {"en": "lip gloss", "zh": "唇蜜"},
                                {"en": "no makeup", "zh": "素顏"},
                                {"en": "heavy makeup", "zh": "濃妝"},
                                {"en": "smokey eyes", "zh": "煙燻眼"},
                            ]
                        },
                    ]
                },
                {
                    "id": "1.3", "title": "髮型",
                    "children": [
                        {
                            "id": "1.3.1", "title": "髮長", "terms": [
                                {"en": "long hair", "zh": "長髮"},
                                {"en": "medium hair", "zh": "中長髮"},
                                {"en": "short hair", "zh": "短髮"},
                                {"en": "shoulder-length", "zh": "及肩"},
                                {"en": "very long hair", "zh": "超長髮"},
                            ]
                        },
                        {
                            "id": "1.3.2", "title": "髮色", "terms": [
                                {"en": "black hair", "zh": "黑髮"},
                                {"en": "brown hair", "zh": "棕髮"},
                                {"en": "blonde", "zh": "金髮"},
                                {"en": "silver hair", "zh": "銀髮"},
                                {"en": "pink hair", "zh": "粉髮"},
                                {"en": "red hair", "zh": "紅髮"},
                                {"en": "blue hair", "zh": "藍髮"},
                                {"en": "gradient hair", "zh": "漸層髮色"},
                            ]
                        },
                        {
                            "id": "1.3.3", "title": "造型", "terms": [
                                {"en": "ponytail", "zh": "馬尾"},
                                {"en": "twin tails", "zh": "雙馬尾"},
                                {"en": "braid", "zh": "辮子"},
                                {"en": "bun", "zh": "丸子頭"},
                                {"en": "bob cut", "zh": "鮑伯頭"},
                                {"en": "hime cut", "zh": "公主切"},
                                {"en": "half-up", "zh": "半紮"},
                                {"en": "side ponytail", "zh": "側馬尾"},
                                {"en": "low ponytail", "zh": "低馬尾"},
                                {"en": "high ponytail", "zh": "高馬尾"},
                                {"en": "french braid", "zh": "法式辮"},
                                {"en": "messy bun", "zh": "隨性丸子頭"},
                            ]
                        },
                        {
                            "id": "1.3.4", "title": "瀏海", "terms": [
                                {"en": "blunt bangs", "zh": "齊瀏海"},
                                {"en": "side-swept bangs", "zh": "斜瀏海"},
                                {"en": "curtain bangs", "zh": "窗簾瀏海"},
                                {"en": "no bangs", "zh": "無瀏海"},
                                {"en": "see-through bangs", "zh": "空氣瀏海"},
                                {"en": "parted bangs", "zh": "分線瀏海"},
                            ]
                        },
                        {
                            "id": "1.3.5", "title": "髮質", "terms": [
                                {"en": "straight", "zh": "直髮"},
                                {"en": "wavy", "zh": "波浪"},
                                {"en": "curly", "zh": "捲髮"},
                                {"en": "silky", "zh": "絲滑"},
                                {"en": "wind-blown", "zh": "風吹效果"},
                                {"en": "glossy hair", "zh": "光澤秀髮"},
                            ]
                        },
                    ]
                },
                {
                    "id": "1.4", "title": "表情",
                    "children": [
                        {
                            "id": "1.4.1", "title": "微笑系", "terms": [
                                {"en": "smile", "zh": "微笑"},
                                {"en": "soft smile", "zh": "淺笑"},
                                {"en": "gentle smile", "zh": "溫柔微笑"},
                                {"en": "grin", "zh": "露齒笑"},
                                {"en": "smirk", "zh": "壞笑"},
                            ]
                        },
                        {
                            "id": "1.4.2", "title": "冷靜系", "terms": [
                                {"en": "calm", "zh": "平靜"},
                                {"en": "neutral", "zh": "中性表情"},
                                {"en": "serious", "zh": "嚴肅"},
                                {"en": "composed", "zh": "沉穩"},
                                {"en": "stoic", "zh": "冷酷"},
                            ]
                        },
                        {
                            "id": "1.4.3", "title": "活潑系", "terms": [
                                {"en": "cheerful", "zh": "開朗"},
                                {"en": "playful", "zh": "俏皮"},
                                {"en": "happy", "zh": "開心"},
                                {"en": "wink", "zh": "眨眼"},
                                {"en": "laugh", "zh": "大笑"},
                                {"en": "pout", "zh": "嘟嘴"},
                            ]
                        },
                        {
                            "id": "1.4.4", "title": "氣質", "terms": [
                                {"en": "gentle", "zh": "溫柔"},
                                {"en": "confident", "zh": "自信"},
                                {"en": "innocent", "zh": "天真"},
                                {"en": "elegant", "zh": "優雅"},
                                {"en": "dreamy", "zh": "夢幻"},
                                {"en": "shy", "zh": "害羞"},
                                {"en": "melancholy", "zh": "憂鬱"},
                            ]
                        },
                    ]
                },
                {
                    "id": "1.5", "title": "視線", "terms": [
                        {"en": "looking at viewer", "zh": "看向觀眾"},
                        {"en": "looking at camera", "zh": "看向鏡頭"},
                        {"en": "looking away", "zh": "看向別處"},
                        {"en": "looking down", "zh": "向下看"},
                        {"en": "looking up", "zh": "向上看"},
                        {"en": "eye contact", "zh": "眼神接觸"},
                        {"en": "looking to the side", "zh": "看向側邊"},
                        {"en": "glancing", "zh": "瞥視"},
                        {"en": "gaze", "zh": "凝視"},
                        {"en": "staring", "zh": "直視"},
                    ]
                },
                {
                    "id": "1.6", "title": "姿勢",
                    "children": [
                        {
                            "id": "1.6.1", "title": "站姿", "terms": [
                                {"en": "standing", "zh": "站立"},
                                {"en": "leaning", "zh": "倚靠"},
                                {"en": "weight shift", "zh": "重心偏移"},
                                {"en": "contrapposto", "zh": "對立式站姿", "tip": "經典S曲線"},
                            ]
                        },
                        {
                            "id": "1.6.2", "title": "坐姿", "terms": [
                                {"en": "sitting", "zh": "坐著"},
                                {"en": "legs crossed", "zh": "翹腳"},
                                {"en": "side-sitting", "zh": "側坐"},
                                {"en": "squatting", "zh": "蹲坐"},
                            ]
                        },
                        {
                            "id": "1.6.3", "title": "其他姿勢", "terms": [
                                {"en": "kneeling", "zh": "跪姿"},
                                {"en": "lying", "zh": "躺臥"},
                                {"en": "crouching", "zh": "蹲下"},
                                {"en": "walking", "zh": "行走"},
                                {"en": "running", "zh": "奔跑"},
                                {"en": "jumping", "zh": "跳躍"},
                                {"en": "from behind", "zh": "背面"},
                                {"en": "profile", "zh": "側面"},
                            ]
                        },
                        {
                            "id": "1.6.4", "title": "手部動作", "terms": [
                                {"en": "holding", "zh": "手持"},
                                {"en": "hands clasped", "zh": "雙手合十"},
                                {"en": "hand on hip", "zh": "手叉腰"},
                                {"en": "arms crossed", "zh": "雙手交叉"},
                                {"en": "hand on head", "zh": "手放頭上"},
                                {"en": "hands behind", "zh": "手放背後"},
                                {"en": "peace sign", "zh": "比V"},
                                {"en": "pointing", "zh": "指向"},
                            ]
                        },
                        {
                            "id": "1.6.5", "title": "身體語言", "terms": [
                                {"en": "elegant posture", "zh": "優雅姿態"},
                                {"en": "dynamic pose", "zh": "動態姿勢"},
                                {"en": "relaxed", "zh": "放鬆"},
                                {"en": "resting", "zh": "休息"},
                                {"en": "turned", "zh": "轉身"},
                            ]
                        },
                    ]
                },
            ]
        },
        {
            "id": "2", "title": "服裝", "title_en": "Clothing",
            "children": [
                {
                    "id": "2.1", "title": "整體類型", "terms": [
                        {"en": "school uniform", "zh": "學生制服"},
                        {"en": "casual", "zh": "休閒裝"},
                        {"en": "sailor", "zh": "水手服"},
                        {"en": "serafuku", "zh": "水手服（日式）", "lang": "ja"},
                        {"en": "office lady", "zh": "OL套裝"},
                        {"en": "idol", "zh": "偶像裝"},
                        {"en": "cosplay", "zh": "角色扮演"},
                        {"en": "maid", "zh": "女僕裝"},
                        {"en": "kimono", "zh": "和服"},
                        {"en": "gothic", "zh": "哥德風"},
                        {"en": "lolita", "zh": "蘿莉塔"},
                        {"en": "military", "zh": "軍裝"},
                        {"en": "formal", "zh": "正裝"},
                        {"en": "nurse", "zh": "護士裝"},
                        {"en": "flight attendant", "zh": "空服員"},
                        {"en": "k-pop", "zh": "韓系偶像"},
                        {"en": "streetwear", "zh": "街頭風"},
                        {"en": "blazer uniform", "zh": "西裝外套制服"},
                    ]
                },
                {
                    "id": "2.2", "title": "上半身",
                    "children": [
                        {
                            "id": "2.2.1", "title": "上衣", "terms": [
                                {"en": "white shirt", "zh": "白襯衫"},
                                {"en": "blouse", "zh": "女衫"},
                                {"en": "sweater", "zh": "毛衣"},
                                {"en": "crop top", "zh": "短版上衣"},
                                {"en": "t-shirt", "zh": "T恤"},
                                {"en": "tank top", "zh": "背心"},
                                {"en": "turtleneck", "zh": "高領"},
                                {"en": "off-shoulder", "zh": "露肩"},
                            ]
                        },
                        {
                            "id": "2.2.2", "title": "外套", "terms": [
                                {"en": "blazer", "zh": "西裝外套"},
                                {"en": "cardigan", "zh": "開襟衫"},
                                {"en": "jacket", "zh": "夾克"},
                                {"en": "vest", "zh": "背心"},
                                {"en": "coat", "zh": "大衣"},
                                {"en": "hoodie", "zh": "連帽衫"},
                            ]
                        },
                        {
                            "id": "2.2.3", "title": "領部", "terms": [
                                {"en": "sailor collar", "zh": "水手領"},
                                {"en": "necktie", "zh": "領帶"},
                                {"en": "ribbon", "zh": "蝴蝶結"},
                                {"en": "bow tie", "zh": "領結"},
                                {"en": "collar", "zh": "領子"},
                            ]
                        },
                        {
                            "id": "2.2.4", "title": "袖子", "terms": [
                                {"en": "long sleeves", "zh": "長袖"},
                                {"en": "short sleeves", "zh": "短袖"},
                                {"en": "sleeveless", "zh": "無袖"},
                                {"en": "rolled sleeves", "zh": "捲袖"},
                                {"en": "puffy sleeves", "zh": "泡泡袖"},
                            ]
                        },
                    ]
                },
                {
                    "id": "2.3", "title": "下半身",
                    "children": [
                        {
                            "id": "2.3.1", "title": "裙", "terms": [
                                {"en": "pleated skirt", "zh": "百褶裙"},
                                {"en": "plaid skirt", "zh": "格紋裙"},
                                {"en": "miniskirt", "zh": "迷你裙"},
                                {"en": "long skirt", "zh": "長裙"},
                                {"en": "A-line skirt", "zh": "A字裙"},
                                {"en": "high-waist skirt", "zh": "高腰裙"},
                            ]
                        },
                        {
                            "id": "2.3.2", "title": "褲", "terms": [
                                {"en": "shorts", "zh": "短褲"},
                                {"en": "jeans", "zh": "牛仔褲"},
                                {"en": "trousers", "zh": "長褲"},
                                {"en": "hot pants", "zh": "熱褲"},
                                {"en": "leggings", "zh": "內搭褲"},
                            ]
                        },
                    ]
                },
                {
                    "id": "2.4", "title": "腿部",
                    "children": [
                        {
                            "id": "2.4.1", "title": "按長度", "terms": [
                                {"en": "ankle socks", "zh": "踝襪"},
                                {"en": "crew socks", "zh": "中筒襪"},
                                {"en": "knee-high socks", "zh": "及膝襪"},
                                {"en": "over-the-knee socks", "zh": "過膝襪"},
                                {"en": "thigh-high stockings", "zh": "大腿襪"},
                            ]
                        },
                        {
                            "id": "2.4.2", "title": "按材質", "terms": [
                                {"en": "sheer pantyhose", "zh": "透膚絲襪"},
                                {"en": "opaque tights", "zh": "不透明褲襪"},
                                {"en": "fishnet stockings", "zh": "漁網襪"},
                                {"en": "cotton socks", "zh": "棉襪"},
                            ]
                        },
                        {
                            "id": "2.4.3", "title": "其他", "terms": [
                                {"en": "bare legs", "zh": "裸腿"},
                                {"en": "garter stockings", "zh": "吊帶襪"},
                                {"en": "leg warmers", "zh": "暖腿套"},
                            ]
                        },
                    ]
                },
                {
                    "id": "2.5", "title": "鞋子", "terms": [
                        {"en": "loafers", "zh": "樂福鞋"},
                        {"en": "high heels", "zh": "高跟鞋"},
                        {"en": "sneakers", "zh": "運動鞋"},
                        {"en": "boots", "zh": "靴子"},
                        {"en": "Mary Jane", "zh": "瑪莉珍鞋"},
                        {"en": "platform shoes", "zh": "厚底鞋"},
                        {"en": "sandals", "zh": "涼鞋"},
                        {"en": "school shoes", "zh": "學生皮鞋"},
                        {"en": "ballet flats", "zh": "芭蕾平底鞋"},
                    ]
                },
                {
                    "id": "2.6", "title": "配飾",
                    "children": [
                        {
                            "id": "2.6.1", "title": "頭飾", "terms": [
                                {"en": "headband", "zh": "髮箍"},
                                {"en": "hair clip", "zh": "髮夾"},
                                {"en": "hair ribbon", "zh": "髮帶"},
                                {"en": "beret", "zh": "貝雷帽"},
                                {"en": "hat", "zh": "帽子"},
                                {"en": "hair flower", "zh": "髮花"},
                            ]
                        },
                        {
                            "id": "2.6.2", "title": "頸飾", "terms": [
                                {"en": "choker", "zh": "頸圈"},
                                {"en": "necklace", "zh": "項鏈"},
                                {"en": "scarf", "zh": "圍巾"},
                            ]
                        },
                        {
                            "id": "2.6.3", "title": "手飾", "terms": [
                                {"en": "bracelet", "zh": "手鏈"},
                                {"en": "ring", "zh": "戒指"},
                                {"en": "watch", "zh": "手錶"},
                                {"en": "gloves", "zh": "手套"},
                            ]
                        },
                        {
                            "id": "2.6.4", "title": "耳飾", "terms": [
                                {"en": "earring", "zh": "耳環"},
                                {"en": "pearl studs", "zh": "珍珠耳釘"},
                                {"en": "hoop earrings", "zh": "圈形耳環"},
                            ]
                        },
                        {
                            "id": "2.6.5", "title": "包包", "terms": [
                                {"en": "bag", "zh": "包包"},
                                {"en": "backpack", "zh": "後背包"},
                                {"en": "school bag", "zh": "書包"},
                                {"en": "handbag", "zh": "手提包"},
                            ]
                        },
                    ]
                },
                {
                    "id": "2.7", "title": "材質花紋", "terms": [
                        {"en": "lace trim", "zh": "蕾絲邊"},
                        {"en": "plaid pattern", "zh": "格紋"},
                        {"en": "ribbed texture", "zh": "羅紋"},
                        {"en": "denim", "zh": "丹寧"},
                        {"en": "leather", "zh": "皮革"},
                        {"en": "silk", "zh": "絲綢"},
                        {"en": "velvet", "zh": "絲絨"},
                        {"en": "chiffon", "zh": "雪紡"},
                        {"en": "polka dot", "zh": "圓點"},
                        {"en": "striped", "zh": "條紋"},
                    ]
                },
            ]
        },
        {
            "id": "3", "title": "場景", "title_en": "Scene",
            "children": [
                {
                    "id": "3.1", "title": "室內", "terms": [
                        {"en": "classroom", "zh": "教室"},
                        {"en": "bedroom", "zh": "臥室"},
                        {"en": "cafe", "zh": "咖啡廳"},
                        {"en": "office", "zh": "辦公室"},
                        {"en": "studio", "zh": "攝影棚"},
                        {"en": "library", "zh": "圖書館"},
                        {"en": "bathroom", "zh": "浴室"},
                        {"en": "kitchen", "zh": "廚房"},
                        {"en": "hallway", "zh": "走廊"},
                        {"en": "locker room", "zh": "更衣室"},
                    ]
                },
                {
                    "id": "3.2", "title": "室外", "terms": [
                        {"en": "urban street", "zh": "城市街道"},
                        {"en": "park", "zh": "公園"},
                        {"en": "shrine", "zh": "神社"},
                        {"en": "rooftop", "zh": "屋頂"},
                        {"en": "train station", "zh": "車站"},
                        {"en": "beach", "zh": "海灘"},
                        {"en": "garden", "zh": "花園"},
                        {"en": "bridge", "zh": "橋"},
                        {"en": "alley", "zh": "巷弄"},
                        {"en": "school gate", "zh": "校門"},
                        {"en": "cherry blossoms", "zh": "櫻花"},
                    ]
                },
                {
                    "id": "3.3", "title": "背景", "terms": [
                        {"en": "white background", "zh": "白色背景"},
                        {"en": "simple background", "zh": "簡單背景"},
                        {"en": "blurred background", "zh": "模糊背景"},
                        {"en": "bokeh background", "zh": "散景背景"},
                        {"en": "gradient background", "zh": "漸層背景"},
                        {"en": "dark background", "zh": "暗色背景"},
                        {"en": "detailed background", "zh": "細緻背景"},
                    ]
                },
                {
                    "id": "3.4", "title": "時段天氣", "terms": [
                        {"en": "sunset", "zh": "夕陽"},
                        {"en": "golden hour", "zh": "黃金時段"},
                        {"en": "overcast", "zh": "陰天"},
                        {"en": "morning light", "zh": "晨光"},
                        {"en": "night", "zh": "夜晚"},
                        {"en": "rainy", "zh": "雨天"},
                        {"en": "cloudy", "zh": "多雲"},
                        {"en": "blue hour", "zh": "藍調時刻"},
                        {"en": "noon", "zh": "正午"},
                    ]
                },
            ]
        },
        {
            "id": "4", "title": "光影", "title_en": "Lighting",
            "children": [
                {
                    "id": "4.1", "title": "光源", "terms": [
                        {"en": "natural daylight", "zh": "自然日光"},
                        {"en": "studio lighting", "zh": "棚燈"},
                        {"en": "cinematic lighting", "zh": "電影感燈光"},
                        {"en": "ring light", "zh": "環形燈"},
                        {"en": "window light", "zh": "窗光"},
                        {"en": "neon light", "zh": "霓虹燈"},
                        {"en": "candlelight", "zh": "燭光"},
                        {"en": "ambient light", "zh": "環境光"},
                    ]
                },
                {
                    "id": "4.2", "title": "方向", "terms": [
                        {"en": "frontal light", "zh": "正面光"},
                        {"en": "side light", "zh": "側光"},
                        {"en": "backlighting", "zh": "逆光"},
                        {"en": "rim light", "zh": "輪廓光"},
                        {"en": "45-degree light", "zh": "45度光"},
                        {"en": "top light", "zh": "頂光"},
                        {"en": "under light", "zh": "底光"},
                    ]
                },
                {
                    "id": "4.3", "title": "品質", "terms": [
                        {"en": "soft lighting", "zh": "柔光"},
                        {"en": "dramatic lighting", "zh": "戲劇性燈光"},
                        {"en": "high contrast", "zh": "高對比"},
                        {"en": "even illumination", "zh": "均勻照明"},
                        {"en": "low key", "zh": "低調光", "tip": "暗部為主"},
                        {"en": "high key", "zh": "高調光", "tip": "亮部為主"},
                    ]
                },
                {
                    "id": "4.4", "title": "效果", "terms": [
                        {"en": "lens flare", "zh": "鏡頭光暈"},
                        {"en": "bloom", "zh": "光暈"},
                        {"en": "catchlights", "zh": "眼神光"},
                        {"en": "glow", "zh": "發光"},
                        {"en": "light rays", "zh": "光線"},
                        {"en": "shadow play", "zh": "光影效果"},
                        {"en": "volumetric light", "zh": "體積光"},
                    ]
                },
            ]
        },
        {
            "id": "5", "title": "鏡頭構圖", "title_en": "Camera & Composition",
            "children": [
                {
                    "id": "5.1", "title": "取景", "terms": [
                        {"en": "full body", "zh": "全身"},
                        {"en": "cowboy shot", "zh": "牛仔鏡頭", "tip": "膝上取景"},
                        {"en": "upper body", "zh": "上半身"},
                        {"en": "portrait", "zh": "肖像"},
                        {"en": "close-up", "zh": "近景"},
                        {"en": "extreme close-up", "zh": "特寫"},
                        {"en": "medium shot", "zh": "中景"},
                        {"en": "wide shot", "zh": "廣角鏡頭"},
                    ]
                },
                {
                    "id": "5.2", "title": "角度", "terms": [
                        {"en": "eye level", "zh": "平視"},
                        {"en": "low angle", "zh": "仰角"},
                        {"en": "high angle", "zh": "俯角"},
                        {"en": "aerial view", "zh": "鳥瞰"},
                        {"en": "3/4 view", "zh": "四分之三角度"},
                        {"en": "dutch angle", "zh": "荷蘭角"},
                        {"en": "worm's eye view", "zh": "蟲視角"},
                    ]
                },
                {
                    "id": "5.3", "title": "鏡頭參數", "terms": [
                        {"en": "85mm lens", "zh": "85mm（人像鏡）", "tip": "最經典人像焦段"},
                        {"en": "50mm lens", "zh": "50mm（標準鏡）"},
                        {"en": "35mm lens", "zh": "35mm（廣角）"},
                        {"en": "135mm lens", "zh": "135mm（長焦人像）"},
                        {"en": "f/1.4", "zh": "大光圈", "tip": "極淺景深"},
                        {"en": "f/1.8", "zh": "大光圈"},
                        {"en": "f/2.8", "zh": "中大光圈"},
                        {"en": "shallow depth of field", "zh": "淺景深"},
                        {"en": "deep depth of field", "zh": "深景深"},
                    ]
                },
                {
                    "id": "5.4", "title": "構圖", "terms": [
                        {"en": "centered composition", "zh": "置中構圖"},
                        {"en": "rule of thirds", "zh": "三分法"},
                        {"en": "symmetrical", "zh": "對稱"},
                        {"en": "golden ratio", "zh": "黃金比例"},
                        {"en": "leading lines", "zh": "引導線"},
                        {"en": "negative space", "zh": "負空間"},
                        {"en": "framing", "zh": "框架構圖"},
                    ]
                },
            ]
        },
        {
            "id": "6", "title": "風格", "title_en": "Style",
            "children": [
                {
                    "id": "6.1", "title": "寫實", "terms": [
                        {"en": "photorealistic", "zh": "照片寫實"},
                        {"en": "raw photo", "zh": "RAW照片感"},
                        {"en": "hyper-realistic", "zh": "超寫實"},
                        {"en": "cinematic realism", "zh": "電影寫實"},
                        {"en": "documentary style", "zh": "紀實風格"},
                        {"en": "DSLR quality", "zh": "單眼品質"},
                    ]
                },
                {
                    "id": "6.2", "title": "動漫", "terms": [
                        {"en": "anime", "zh": "動漫風"},
                        {"en": "illustration", "zh": "插畫"},
                        {"en": "--niji 5", "zh": "Midjourney動漫模式", "tip": "MJ專用參數"},
                        {"en": "manga style", "zh": "漫畫風"},
                        {"en": "cel shading", "zh": "賽璐璐著色"},
                        {"en": "flat color", "zh": "平塗"},
                    ]
                },
                {
                    "id": "6.3", "title": "手繪", "terms": [
                        {"en": "pencil sketch", "zh": "鉛筆素描"},
                        {"en": "watercolor", "zh": "水彩"},
                        {"en": "oil painting", "zh": "油畫"},
                        {"en": "pastel drawing", "zh": "粉彩"},
                        {"en": "ink wash", "zh": "水墨"},
                        {"en": "charcoal", "zh": "炭筆"},
                    ]
                },
                {
                    "id": "6.4", "title": "3D/特殊", "terms": [
                        {"en": "3d render", "zh": "3D渲染"},
                        {"en": "isometric", "zh": "等距"},
                        {"en": "miniature", "zh": "微縮"},
                        {"en": "diorama", "zh": "場景模型"},
                        {"en": "pixel art", "zh": "像素風"},
                        {"en": "voxel art", "zh": "體素風"},
                    ]
                },
                {
                    "id": "6.5", "title": "美學", "terms": [
                        {"en": "vintage", "zh": "復古"},
                        {"en": "retro", "zh": "懷舊"},
                        {"en": "kawaii", "zh": "可愛"},
                        {"en": "cyberpunk", "zh": "賽博龐克"},
                        {"en": "film look", "zh": "底片感"},
                        {"en": "dreamy aesthetic", "zh": "夢幻美學"},
                        {"en": "dark academia", "zh": "暗黑學院風"},
                        {"en": "cottagecore", "zh": "田園風"},
                    ]
                },
            ]
        },
        {
            "id": "7", "title": "色彩", "title_en": "Color",
            "children": [
                {
                    "id": "7.1", "title": "基本色", "terms": [
                        {"en": "red", "zh": "紅"},
                        {"en": "blue", "zh": "藍"},
                        {"en": "black", "zh": "黑"},
                        {"en": "white", "zh": "白"},
                        {"en": "pink", "zh": "粉"},
                        {"en": "gold", "zh": "金"},
                        {"en": "navy", "zh": "海軍藍"},
                        {"en": "green", "zh": "綠"},
                        {"en": "purple", "zh": "紫"},
                        {"en": "orange", "zh": "橘"},
                        {"en": "silver", "zh": "銀"},
                        {"en": "beige", "zh": "米色"},
                    ]
                },
                {
                    "id": "7.2", "title": "色調", "terms": [
                        {"en": "warm tone", "zh": "暖色調"},
                        {"en": "cool tone", "zh": "冷色調"},
                        {"en": "pastel", "zh": "粉彩色"},
                        {"en": "vibrant", "zh": "鮮豔"},
                        {"en": "desaturated", "zh": "低飽和"},
                        {"en": "monochrome", "zh": "單色"},
                        {"en": "muted colors", "zh": "柔和色"},
                        {"en": "high saturation", "zh": "高飽和"},
                    ]
                },
                {
                    "id": "7.3", "title": "後製", "terms": [
                        {"en": "color grading", "zh": "調色"},
                        {"en": "color palette", "zh": "色盤"},
                        {"en": "sRGB", "zh": "sRGB色域"},
                        {"en": "teal and orange", "zh": "青橘調色", "tip": "電影感常用"},
                        {"en": "cross-process", "zh": "交叉沖洗"},
                    ]
                },
            ]
        },
        {
            "id": "8", "title": "品質控制", "title_en": "Quality Control",
            "children": [
                {
                    "id": "8.1", "title": "正面品質詞", "terms": [
                        {"en": "best quality", "zh": "最佳品質"},
                        {"en": "masterpiece", "zh": "傑作"},
                        {"en": "8k", "zh": "8K解析度"},
                        {"en": "ultra detailed", "zh": "超精細"},
                        {"en": "sharp focus", "zh": "銳利對焦"},
                        {"en": "high resolution", "zh": "高解析度"},
                        {"en": "absurdres", "zh": "超高解析度", "tip": "NovelAI/SD常用"},
                        {"en": "intricate details", "zh": "精密細節"},
                        {"en": "professional photo", "zh": "專業攝影"},
                    ]
                },
                {
                    "id": "8.2", "title": "負面提示詞", "terms": [
                        {"en": "bad anatomy", "zh": "解剖錯誤", "neg": True},
                        {"en": "extra fingers", "zh": "多餘手指", "neg": True},
                        {"en": "text", "zh": "文字", "neg": True},
                        {"en": "watermark", "zh": "浮水印", "neg": True},
                        {"en": "blurry", "zh": "模糊", "neg": True},
                        {"en": "deformed", "zh": "變形", "neg": True},
                        {"en": "low quality", "zh": "低品質", "neg": True},
                        {"en": "worst quality", "zh": "最差品質", "neg": True},
                        {"en": "ugly", "zh": "醜陋", "neg": True},
                        {"en": "duplicate", "zh": "重複", "neg": True},
                        {"en": "cropped", "zh": "裁切", "neg": True},
                        {"en": "mutation", "zh": "突變", "neg": True},
                        {"en": "extra limbs", "zh": "多餘肢體", "neg": True},
                    ]
                },
                {
                    "id": "8.3", "title": "平台語法", "terms": [
                        {"en": "--ar 2:3", "zh": "長寬比 2:3（直式）", "tip": "Midjourney"},
                        {"en": "--ar 3:2", "zh": "長寬比 3:2（橫式）", "tip": "Midjourney"},
                        {"en": "--ar 1:1", "zh": "長寬比 1:1（方形）", "tip": "Midjourney"},
                        {"en": "--niji 5", "zh": "動漫模式", "tip": "Midjourney"},
                        {"en": "--v 6", "zh": "版本6", "tip": "Midjourney"},
                        {"en": "(keyword:1.4)", "zh": "關鍵字加權 1.4", "tip": "SD/NAI語法"},
                        {"en": "mix4", "zh": "混合模式4", "tip": "特定平台"},
                        {"en": "--style raw", "zh": "RAW風格", "tip": "Midjourney"},
                        {"en": "--chaos N", "zh": "混亂度", "tip": "Midjourney，N=0-100"},
                    ]
                },
            ]
        },
        {
            "id": "9", "title": "特殊技法", "title_en": "Advanced Techniques",
            "children": [
                {
                    "id": "9.1", "title": "身份鎖定", "terms": [
                        {"en": "identity_lock", "zh": "身份鎖定"},
                        {"en": "face_accuracy", "zh": "臉部精確度"},
                        {"en": "maintain the exact same person", "zh": "保持同一人物"},
                        {"en": "consistent character", "zh": "角色一致性"},
                        {"en": "same face", "zh": "相同臉部"},
                    ]
                },
                {
                    "id": "9.2", "title": "服裝鎖定", "terms": [
                        {"en": "outfit_lock", "zh": "服裝鎖定"},
                        {"en": "do not alter clothing", "zh": "不要改變服裝"},
                        {"en": "keep original outfit", "zh": "保持原始服裝"},
                    ]
                },
                {
                    "id": "9.3", "title": "技術", "terms": [
                        {"en": "LoRA", "zh": "低秩適配", "tip": "微調模型技術"},
                        {"en": "controlnet", "zh": "控制網路", "tip": "姿勢/邊緣控制"},
                        {"en": "inpainting", "zh": "局部重繪"},
                        {"en": "img2img", "zh": "圖生圖"},
                        {"en": "reference image", "zh": "參考圖"},
                        {"en": "txt2img", "zh": "文生圖"},
                        {"en": "outpainting", "zh": "外擴繪製"},
                        {"en": "depth map", "zh": "深度圖"},
                        {"en": "openpose", "zh": "姿態偵測"},
                    ]
                },
            ]
        },
    ]
}


def count_frequencies_from_db(db_path):
    """從 DB 的 prompt 欄位統計每個詞彙的出現次數"""
    freq_map = {}
    if not db_path.exists():
        log.warning(f"DB 不存在: {db_path}，跳過頻率統計")
        return freq_map

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # 取得所有 prompt
        cursor.execute("SELECT prompt FROM images WHERE prompt IS NOT NULL AND prompt != ''")
        rows = cursor.fetchall()
        conn.close()

        all_text = " ".join(r[0].lower() for r in rows)
        log.info(f"從 DB 讀取 {len(rows)} 筆 prompt")
        return all_text
    except Exception as e:
        log.error(f"讀取 DB 失敗: {e}")
        return ""


def count_term_in_text(term, text):
    """計算 term 在所有 prompt 文本中出現的次數（不區分大小寫）"""
    term_lower = term.lower()
    count = 0
    start = 0
    while True:
        idx = text.find(term_lower, start)
        if idx == -1:
            break
        count += 1
        start = idx + len(term_lower)
    return count


def inject_frequencies(node, all_text):
    """遞迴為樹中所有 term 注入頻率"""
    term_count = 0
    node_count = 0

    if "terms" in node:
        for t in node["terms"]:
            en = t["en"]
            freq = count_term_in_text(en, all_text)
            if freq > 0:
                t["freq"] = freq
            term_count += len(node["terms"])
        node_count += 1

    if "children" in node:
        for child in node["children"]:
            tc, nc = inject_frequencies(child, all_text)
            term_count += tc
            node_count += nc

    return term_count, node_count


def main():
    log.info("=== 開始建立樹狀提示詞辭典 ===")

    # 讀取 DB 文本
    all_text = count_frequencies_from_db(DB_PATH)

    tree = TREE.copy()
    total_terms = 0
    total_nodes = 0

    for chapter in tree["chapters"]:
        tc, nc = inject_frequencies(chapter, all_text)
        total_terms += tc
        total_nodes += nc
        log.info(f"第{chapter['id']}章 [{chapter['title']}]: {tc} 詞彙, {nc} 節點")

    tree["metadata"] = {
        "total_chapters": len(tree["chapters"]),
        "total_leaf_nodes": total_nodes,
        "total_terms": total_terms,
        "source_db": str(DB_PATH.name),
        "description": "樹狀提示詞辭典 - 9章分類，手動策展 + DB 頻率統計"
    }

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    log.info(f"輸出: {OUT_PATH}")
    log.info(f"總計: {len(tree['chapters'])} 章, {total_nodes} 葉節點, {total_terms} 詞彙")
    log.info("=== 完成 ===")


if __name__ == "__main__":
    main()
