import re
import unicodedata


class DapaoPromptLineRepeatNode:
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
                "📝 提示词": ("STRING", {"default": "", "multiline": True, "tooltip": "需要复制的提示词"}),
                "🧰 字符串预处理": (preprocess_options, {"default": "不改变"}),
                "🔢 复制数量": ("INT", {"default": 3, "min": 1, "max": 9999, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("📝 复制结果", "🔢 字数")
    FUNCTION = "repeat"
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

    def repeat(self, **kwargs):
        text = str(kwargs.get("📝 提示词", ""))
        option = str(kwargs.get("🧰 字符串预处理", "不改变"))
        repeat_count = int(kwargs.get("🔢 复制数量", 3))

        if option == "统计字数":
            char_count = self._count_nonspace_chars(text)
            return (str(char_count), char_count)

        processed_text = self._apply_preprocess(text, option)
        result = "\n".join(processed_text for _ in range(repeat_count))
        char_count = self._count_nonspace_chars(result)
        return (result, char_count)


NODE_CLASS_MAPPINGS = {
    "DapaoPromptLineRepeatNode": DapaoPromptLineRepeatNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoPromptLineRepeatNode": "🐧提示词行复制@炮老师的小课堂",
}
