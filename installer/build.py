"""做出 Windows 安裝檔，放在 installer/dist：GameClicker-Setup-Windows-<版本>.exe
用法：python installer/build.py v1.2.3 [--test]
--test 做測試用的安裝檔（不同的 AppId、不建捷徑），在開發的電腦上試裝不會蓋掉原本的捷徑。
需要：Inno Setup 6（winget install JRSoftware.InnoSetup）、PyInstaller（pip install pyinstaller）。"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "build")
ISCC_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    version, test = args[0], "--test" in sys.argv
    code = open(os.path.join(ROOT, "autoclicker.py"), encoding="utf-8").read()
    in_code = re.search(r'^VERSION = "([^"]+)"', code, re.M).group(1)
    if in_code != version.lstrip("v"):
        sys.exit(f"版本不一致：autoclicker.py 的 VERSION 是 {in_code}，但你要做的是 {version}")
    iscc = next((p for p in ISCC_PATHS if os.path.exists(p)), None)
    if not iscc:
        sys.exit("找不到 Inno Setup 6，請先安裝：winget install JRSoftware.InnoSetup")

    if not os.path.exists(os.path.join(ROOT, "gameclicker.ico")):
        subprocess.check_call([sys.executable, os.path.join(HERE, "make_icon.py")])
    shutil.rmtree(BUILD, ignore_errors=True)
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--name", "GameClicker",
        "--icon", os.path.join(ROOT, "gameclicker.ico"),
        "--add-data", os.path.join(ROOT, "gameclicker.ico") + os.pathsep + ".",
        "--distpath", os.path.join(BUILD, "dist"), "--workpath", os.path.join(BUILD, "work"),
        "--specpath", BUILD, os.path.join(ROOT, "autoclicker.py")])

    cmd = [iscc, f"/DAppVersion={version}"] + (["/DTESTBUILD"] if test else []) + [os.path.join(HERE, "gameclicker.iss")]
    subprocess.check_call(cmd)
    print("完成：", os.path.join(HERE, "dist"))


if __name__ == "__main__":
    main()
