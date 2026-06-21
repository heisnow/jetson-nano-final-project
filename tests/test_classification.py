from __future__ import annotations

import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import analyze_text  # noqa: E402


class ClassificationRuleTests(unittest.TestCase):
    def assert_classifies(self, text: str, item: str, category: str) -> None:
        result = analyze_text(text)
        self.assertEqual(result["item_name"], item)
        self.assertEqual(result["category"], category)
        self.assertGreater(result["confidence"], 0.35)

    def test_original_core_items_still_classify(self) -> None:
        cases = [
            ("寶特瓶 PET", "寶特瓶", "資源回收 / 塑膠類"),
            ("紙箱 瓦楞紙", "紙箱", "資源回收 / 廢紙類"),
            ("衛生紙 紙巾", "衛生紙", "一般垃圾"),
            ("鋁箔包", "鋁箔包", "資源回收 / 紙容器"),
            ("玻璃瓶", "玻璃瓶", "資源回收 / 玻璃類"),
            ("鐵鋁罐", "鐵鋁罐", "資源回收 / 金屬類"),
        ]
        for text, item, category in cases:
            with self.subTest(text=text):
                self.assert_classifies(text, item, category)

    def test_common_waste_cases_from_investigation_are_not_unknown(self) -> None:
        cases = [
            ("口罩", "口罩", "一般垃圾"),
            ("陶瓷碗", "陶瓷與非容器玻璃", "一般垃圾"),
            ("筷子", "筷子與小型餐具", "一般垃圾"),
            ("衣服", "乾淨舊衣物", "資源回收 / 舊衣類"),
            ("鞋子", "鞋類", "依地方規定回收"),
            ("牙刷", "牙刷與牙膏軟管", "一般垃圾"),
            ("牙膏", "牙刷與牙膏軟管", "一般垃圾"),
            ("雨傘", "雨傘", "依地方規定回收"),
            ("燈泡", "照明光源", "資源回收 / 照明光源"),
            ("充電線", "小型電子與線材", "依地方規定回收 / 小家電與3C"),
            ("耳機", "小型電子與線材", "依地方規定回收 / 小家電與3C"),
            ("手機", "小型電子與線材", "依地方規定回收 / 小家電與3C"),
            ("藥品包裝", "藥品包裝", "依材質判斷"),
            ("泡泡紙", "塑膠薄膜與泡泡紙", "一般垃圾"),
            ("保鮮膜", "塑膠薄膜與泡泡紙", "一般垃圾"),
            ("塑膠吸管", "筷子與小型餐具", "一般垃圾"),
            ("外送紙袋", "外送紙袋", "資源回收 / 廢紙類"),
            ("廢油", "廢食用油", "依地方規定回收 / 廢油"),
            ("骨頭", "骨頭與貝殼", "一般垃圾"),
            ("貝殼", "骨頭與貝殼", "一般垃圾"),
            ("水果網套", "水果網套", "依地方規定回收"),
        ]
        for text, item, category in cases:
            with self.subTest(text=text):
                self.assert_classifies(text, item, category)

    def test_synonyms_hit_same_rules(self) -> None:
        cases = [
            ("外科口罩", "口罩"),
            ("馬克杯", "陶瓷與非容器玻璃"),
            ("免洗筷", "筷子與小型餐具"),
            ("球鞋", "鞋類"),
            ("日光燈", "照明光源"),
            ("傳輸線", "小型電子與線材"),
            ("泡殼包裝", "藥品包裝"),
            ("氣泡紙", "塑膠薄膜與泡泡紙"),
            ("牛皮紙袋", "外送紙袋"),
            ("炸油", "廢食用油"),
            ("蟹殼", "骨頭與貝殼"),
            ("泡棉網", "水果網套"),
        ]
        for text, item in cases:
            with self.subTest(text=text):
                result = analyze_text(text)
                self.assertEqual(result["item_name"], item)
                self.assertNotEqual(result["item_name"], "未知物品")


if __name__ == "__main__":
    unittest.main()
