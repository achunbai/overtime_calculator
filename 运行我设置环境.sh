#!/bin/bash

# 获取当前系统类型
OS_TYPE=$(uname)
SYS_ARCH=$(uname -m)

compare_versions() {
    if [[ $1 == $2 ]]
    then
        return 0
    fi

    local IFS=.
    local i ver1=($1) ver2=($2)

    # 填充版本号
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done

    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            ver2[i]=0
        fi

        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi

        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done

    return 0
}

if [ "$OS_TYPE" == "Darwin" ]; then
    echo "当前系统是 macOS"
    # 检查是否安装了 Homebrew
    if command -v brew &> /dev/null; then
        echo "Homebrew 已安装"
    else
        echo "Homebrew 未安装，安装Commandline Tools for Xcode..."
        xcode-select --install
        if [ $? -ne 0 ]; then
            echo "安装 Commandline Tools for Xcode 失败"
            exit 1
        fi

        echo "使用北京外国语大学镜像源安装Homebrew..."
        export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.bfsu.edu.cn/git/homebrew/brew.git"
        export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-core.git"
        export HOMEBREW_PIP_INDEX_URL="https://mirrors.bfsu.edu.cn/pypi/web/simple"
        export HOMEBREW_INSTALL_FROM_API=1
        git clone --depth=1 https://mirrors.bfsu.edu.cn/git/homebrew/install.git brew-install
        /bin/bash brew-install/install.sh
        if [ $? -ne 0 ]; then
            echo "安装 Homebrew 失败"
            rm -rf brew-install
            exit 1
        fi
        rm -rf brew-install

        if [ "$SYS_ARCH" == "arm64" ] || [ "$SYS_ARCH" == "aarch64" ]; then
            # Apple Silicon Mac
            test -r ~/.bash_profile && echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.bash_profile
            test -r ~/.zprofile && echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        fi
        export HOMEBREW_API_DOMAIN="https://mirrors.bfsu.edu.cn/homebrew-bottles/api"
        export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.bfsu.edu.cn/homebrew-bottles"
        export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-core.git"
        brew tap --custom-remote --force-auto-update homebrew/core https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-core.git
        brew tap --custom-remote --force-auto-update homebrew/cask https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-cask.git
        brew tap --custom-remote --force-auto-update homebrew/command-not-found https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-command-not-found.git
        brew update
        if [ $? -ne 0 ]; then
            echo "更新 Homebrew 失败"
            exit 1
        fi

        test -r ~/.zprofile && echo 'export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.bfsu.edu.cn/git/homebrew/brew.git"' >> ~/.zprofile  # zsh
        test -r ~/.zprofile && echo 'export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.bfsu.edu.cn/git/homebrew/homebrew-core.git"' >> ~/.zprofile
    fi

    # 检查 Python 是否安装，并且版本大于 3.9
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        compare_versions $PYTHON_VERSION "3.9"
        if [ $? -eq 1 ] || [ $? -eq 0 ]; then
            echo "Python 版本大于或等于 3.9: $PYTHON_VERSION"
        else
            echo "Python 版本小于 3.9: $PYTHON_VERSION，安装最新版本的 Python..."
            brew install python
            if [ $? -ne 0 ]; then
                echo "安装 Python 失败"
                exit 1
            fi
        fi
    else
        echo "Python 未安装，安装最新版本的 Python..."
        brew install python
        if [ $? -ne 0 ]; then
            echo "安装 Python 失败"
            exit 1
        fi
    fi

elif [ "$OS_TYPE" == "Linux" ]; then
    echo "当前系统是 Linux"
    # 检查发行版
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "发行版: $NAME"

        # 检查 Python 是否安装，并且版本大于 3.9
        if command -v python3 &> /dev/null; then
            PYTHON_VERSION=$(python3 --version | awk '{print $2}')
            compare_versions $PYTHON_VERSION "3.9"
            if [ $? -eq 1 ] || [ $? -eq 0 ]; then
                echo "Python 版本大于或等于 3.9: $PYTHON_VERSION"
            else
                echo "Python 版本小于 3.9: $PYTHON_VERSION，安装最新版本的 Python..."
                if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                    sudo apt update
                    sudo apt install -y python3 python3-pip
                    if [ $? -ne 0 ]; then
                        echo "安装 Python 失败"
                        exit 1
                    fi
                elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
                    sudo yum install -y python3 python3-pip
                    if [ $? -ne 0 ]; then
                        echo "安装 Python 失败"
                        exit 1
                    fi
                elif [ "$ID" == "arch" ]; then
                    sudo pacman -Syu --noconfirm python python-pip
                    if [ $? -ne 0 ]; then
                        echo "安装 Python 失败"
                        exit 1
                    fi
                else
                    echo "未知的 Linux 发行版: $ID"
                    exit 1
                fi
            fi
        else
            echo "Python 未安装，安装最新版本的 Python..."
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt update
                sudo apt install -y python3 python3-pip
                if [ $? -ne 0 ]; then
                    echo "安装 Python 失败"
                    exit 1
                fi
            elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
                sudo yum install -y python3 python3-pip
                if [ $? -ne 0 ]; then
                    echo "安装 Python 失败"
                    exit 1
                fi
            elif [ "$ID" == "arch" ]; then
                sudo pacman -Syu --noconfirm python python-pip
                if [ $? -ne 0 ]; then
                    echo "安装 Python 失败"
                    exit 1
                fi
            else
                echo "未知的 Linux 发行版: $ID"
                exit 1
            fi
        fi
    else
        echo "无法确定发行版"
        exit 1
    fi
else
    echo "未知的操作系统类型: $OS_TYPE"
    exit 1
fi

echo "Python检查完毕，使用北京外国语大学镜像源安装依赖..."

python3 -m pip config set global.index-url https://mirrors.bfsu.edu.cn/pypi/web/simple
if [ $? -ne 0 ]; then
    echo "设置 pip 镜像源失败"
    exit 1
fi

python3 -m pip install --upgrade pip --break-system-packages
if [ $? -ne 0 ]; then
    echo "升级 pip 失败"
    exit 1
fi

if [ -f requirements.txt ]; then
    python3 -m pip install -r requirements.txt --break-system-packages
    if [ $? -ne 0 ]; then
        echo "安装依赖失败"
        exit 1
    fi
else
    echo "未找到 requirements.txt 文件，跳过依赖安装"
fi

echo "一切就绪，现在开始运行计算器..."

python3 calculator.py
if [ $? -ne 0 ]; then
    echo "运行计算器失败"
    exit 1
fi