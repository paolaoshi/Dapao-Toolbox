import random
import re
import secrets
import unicodedata


class DapaoRandomPromptLineExtractNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        preprocess_options = [
            "不改变",
            "取数字",
            "取字母",
            "转大写",
            "转小写",
            "取中文",
            "去标点",
            "去换行",
            "去空行",
            "去空格",
            "去格式",
            "统计字数",
        ]

        return {
            "required": {
                "📝 多行文本": ("STRING", {"default": "", "multiline": True, "tooltip": "每行一个候选提示词"}),
                "🧰 字符串预处理": (preprocess_options, {"default": "不改变"}),
                "🔢 提取行数": ("INT", {"default": 1, "min": 1, "max": 9999, "step": 1}),
                "🎲 随机种子": ("INT", {"default": 0, "min": 0, "max": 0x7FFFFFFF, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("📝 提取结果", "🔢 字数")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "extract"
    CATEGORY = "🤖Dapao-Toolbox/🗼字符串处理"

    def _remove_punctuation(self, text: str) -> str:
        return "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))

    def _count_nonspace_chars(self, text: str) -> int:
        return sum(1 for ch in text if not ch.isspace())

    def _apply_preprocess(self, text: str, option: str) -> str:
        if option == "不改变":
            return text
        if option == "取数字":
            return "".join(ch for ch in text if ch.isdigit() or ch == "\n")
        if option == "取字母":
            return "".join(ch for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "\n")
        if option == "转大写":
            return text.upper()
        if option == "转小写":
            return text.lower()
        if option == "取中文":
            return "".join(ch for ch in text if ("\u4e00" <= ch <= "\u9fff") or ch == "\n")
        if option == "去标点":
            return self._remove_punctuation(text)
        if option == "去换行":
            return text.replace("\r\n", "").replace("\n", "").replace("\r", "")
        if option == "去空行":
            return "\n".join(ln for ln in text.splitlines() if ln.strip() != "")
        if option == "去空格":
            return "".join(ch for ch in text if (unicodedata.category(ch) != "Zs" and ch != "\t"))
        if option == "去格式":
            normalized_lines = []
            for ln in text.splitlines():
                normalized = re.sub(r"\s+", " ", ln.replace("\t", " ").replace("\r", " ")).strip()
                if normalized != "":
                    normalized_lines.append(normalized)
            return "\n".join(normalized_lines)
        return text

    def extract(self, **kwargs):
        text = str(kwargs.get("📝 多行文本", ""))
        option = str(kwargs.get("🧰 字符串预处理", "不改变"))
        pick_count = int(kwargs.get("🔢 提取行数", 1))
        seed = int(kwargs.get("🎲 随机种子", 0))

        lines = [ln for ln in text.splitlines() if ln.strip() != ""]

        if not lines:
            return ("", 0)

        rng = random.Random(seed if seed != 0 else secrets.randbelow(0x7FFFFFFF))

        if pick_count <= 1:
            picked_indices = [rng.randrange(len(lines))]
        else:
            if pick_count <= len(lines):
                picked_indices = rng.sample(range(len(lines)), k=pick_count)
            else:
                picked_indices = list(range(len(lines)))
                remaining = pick_count - len(lines)
                picked_indices.extend(rng.randrange(len(lines)) for _ in range(remaining))

        picked_lines = [lines[i] for i in sorted(picked_indices)]

        if option == "统计字数":
            selected_text = "\n".join(picked_lines)
            char_count = self._count_nonspace_chars(selected_text)
            return ([str(char_count)], char_count)

        picked_processed = [self._apply_preprocess(ln, option) for ln in picked_lines]
        char_count = self._count_nonspace_chars("\n".join(picked_processed))
        return (picked_processed, char_count)


NODE_CLASS_MAPPINGS = {
    "DapaoRandomPromptLineExtractNode": DapaoRandomPromptLineExtractNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoRandomPromptLineExtractNode": "🐧随机提示词行提取@炮老师的小课堂",
}
