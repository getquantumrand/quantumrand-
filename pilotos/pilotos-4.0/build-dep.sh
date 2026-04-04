#!/bin/bash 

echo_to_terminal() {
    exec 3>&1
    echo "$1"
    exec 1>&3
}

echo_to_terminal "$(date): 开始编译！"

THREADS=${1:-4}
INSTALL_PREFIX=${2:-$HOME/local}  # 默认安装路径 ~/local
QPANDA3_INSTALL_PREFIX=${2:-$HOME/local/QPanda3} 

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/ThirdParty"

#if [ ! -d "$INSTALL_PREFIX" ]; then
#    mkdir -p "$INSTALL_PREFIX"
#fi

echo_error_exit() {
    echo_to_terminal "安装失败，见详细日志./build_output.txt"
    exit 1
}

# 进入 ThirdParty 目录
cd "$SRC_DIR" || echo_error_exit

echo_to_terminal "install-dir: $INSTALL_PREFIX"
echo_to_terminal "i3333333333333"

extract_and_cd() {
    local archive="$1"
    local dir="$2"
    
    if [ -d "$dir" ]; then
        echo_to_terminal "发现已存在的 $dir 目录，删除旧目录...重新解压"
        rm -rf "$dir"
    fi
    
    # tar xzf "$archive" --warning=none > /dev/null || echo_error_exit

    case "$archive" in
        *.tar.gz|*.tgz)
            tar xzf "$archive" --warning=none > /dev/null || echo_error_exit
            ;;
        *.zip)
            unzip -q "$archive" -d . > /dev/null || echo_error_exit
            ;;
        *)
            echo_error_exit "错误：不支持的文件格式 '$archive'"
            ;;
    esac

    cd "$dir" || echo_error_exit
}

# 检测函数，仅检查用户目录
is_installed() {
    local libname="$1"
    [ -f "$INSTALL_PREFIX/lib/$libname.so" ] || [ -f "$INSTALL_PREFIX/lib/$libname.a" ]
}


install_openssl() {
    # if command -v openssl &>/dev/null && openssl version | grep -q "1.1.1m"; then
    #     echo_to_terminal "OpenSSL 已安装"
    #     return
    # fi
    if [ -d "$INSTALL_PREFIX/include/openssl" ]; then
        echo_to_terminal "OpenSSL 已安装"
        return
    fi
	
    extract_and_cd openssl-1.1.1m.tar.gz openssl-1.1.1m
	
    ./config --prefix="$INSTALL_PREFIX" --openssldir="ssl" || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "OpenSSL 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_curl() {
    # if command -v curl &>/dev/null && curl --version | grep -q "curl 7.82.0"; then
    #     echo_to_terminal "Curl 已安装"
    #     return
    # fi
    if is_installed "libcurl"; then
        echo_to_terminal "Curl 已安装"
        return
    fi
    extract_and_cd curl-7.82.0.tar.gz curl-7.82.0
    ./configure --with-openssl --prefix="$INSTALL_PREFIX" || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "Curl 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_libzmq() {
    # if pkg-config --exists libzmq; then
    #     echo_to_terminal "libzmq 已安装"
    #     return
    # fi
    if is_installed "libzmq"; then
        echo_to_terminal "libzmq 已安装"
        return
    fi
    extract_and_cd zeromq-4.3.4.tar.gz zeromq-4.3.4
    mkdir build && cd build || echo_error_exit
    cmake .. -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "libzmq 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_libevent() {
    # if pkg-config --exists libevent; then
    #     echo_to_terminal "libevent 已安装"
    #     return
    # fi
    if is_installed "libevent"; then
        echo_to_terminal "libevent 已安装"
        return
    fi
    extract_and_cd libevent-2.1.12-stable.tar.gz libevent-2.1.12-stable
    mkdir build && cd build || echo_error_exit
    cmake .. -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "libevent 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_hiredis() {
    # if pkg-config --exists hiredis; then
    #     echo_to_terminal "Hiredis 已安装"
    #     return
    # fi
    if is_installed "libhiredis"; then
        echo_to_terminal "Hiredis 已安装"
        return
    fi
    if [ ! -d "hiredis" ]; then
        git clone https://github.com/redis/hiredis.git || echo_error_exit
    fi
    cd hiredis || echo_error_exit
    if [ ! -d "build" ]; then
        mkdir build || echo_error_exit
    fi
    cd build || echo_error_exit
    cmake .. -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "Hiredis 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_mongodbcdriver() {
    if is_installed "libmongoc-2.0"; then
        echo_to_terminal "mongoDB_C_Driver 已安装"
        return
    fi
    extract_and_cd mongo-c-driver-2.0.1.tar.gz mongo-c-driver-2.0.1 || echo_error_exit
    mkdir cmake-build || echo_error_exit
    cd cmake-build || echo_error_exit
    cmake -DENABLE_AUTOMATIC_INIT_AND_CLEANUP=OFF -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" .. || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "mongoDB_C_Driver 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_mongodbcxxdriver() {
    if is_installed "libmongocxx"; then
        echo_to_terminal "mongoDB_CXX_Driver 已安装"
        return
    fi
    extract_and_cd mongo-cxx-driver-r4.1.1.tar.gz mongo-cxx-driver-r4.1.1 || echo_error_exit
    mkdir cmake-build || echo_error_exit
    cd cmake-build || echo_error_exit
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" -DLIBMONGOC_DIR="$INSTALL_PREFIX" \
	-DLIBBSON_DIR="$INSTALL_PREFIX" -DBUILD_VERSION="4.1.1" \
    -DBUILD_SHARED_LIBS=ON \
    .. || echo_error_exit
    # make EP_mnmlstc_core || echo_error_exit # 不再需要单独构建 EP_mnmlstc_core（现代版本已内置 polyfill）
    # 由git clone导致的停滞，可手动 git clone https://github.com/mnmlstc/core.git 后sudo make EP_mnmlstc_core
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "mongoDB_CXX_Driver 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_qhetu() {
    if is_installed "libQHetu-3"; then
        echo_to_terminal "libQHetu-3 已安装"
        return
    fi
    extract_and_cd qhetu-software_verify.zip qhetu-software_verify || echo_error_exit
    python3 configure.py || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    echo_to_terminal "QHetu-3 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_system_packages() {
    for pkg in libmysqlclient-dev uuid-dev libboost-all-dev protobuf-compiler libprotobuf-dev redis-server; do
        if dpkg -l | grep -q "$pkg"; then
            echo_to_terminal "$pkg 已安装"
        else
            echo_to_terminal "安装 $pkg ..."
            apt-get install -y "$pkg" || echo_error_exit
        fi
    done
}

install_Qpanda2() {
    extract_and_cd qpanda-2-develop-*.tar.gz qpanda-2-develop || echo_error_exit
    mkdir -p build && cd build || echo_error_exit
    cmake -DFIND_CUDA=OFF -DUSE_CHEMIQ=OFF -DUSE_PYQPANDA=OFF -DUSE_EXTENSION=ON -DUSE_GTEST=OFF .. || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    ldconfig || echo_error_exit
    echo_to_terminal "Qpanda 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_Qpanda3() {
    extract_and_cd qpanda-3-develop-*.tar.gz qpanda-3-develop || echo_error_exit
    mkdir -p build && cd build || echo_error_exit
    cmake -DCMAKE_INSTALL_PREFIX="$QPANDA3_INSTALL_PREFIX" -DBUILD_DOCS=OFF -DUSE_PYQPANDA=OFF -DFIND_CUDA=OFF -DCUDA_FOUND=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DUSE_GTEST=OFF .. || echo_error_exit
    make -j${THREADS} || echo_error_exit
    make install || echo_error_exit
    ldconfig || echo_error_exit
    echo_to_terminal "Qpanda3 安装完成"
    cd "$SRC_DIR" || echo_error_exit
}

install_politos() {
    cd pilotos
    if [ ! -d "build" ]; then
        mkdir build || echo_error_exit
    fi
    cd build
    echo_to_terminal "开始编译 QPolitOS!"
    cmake -DTHIRD_PARTY_INSTALL_PATH="$INSTALL_PREFIX" -DQPANDA3_INSTALL_DIR="$QPANDA3_INSTALL_PREFIX" .. # 默认BUILD类型：RelWithDebInfo
    make -j${THREADS} || echo_error_exit
    echo_to_terminal "QPolitOS 编译完成!"
    cd "$SRC_DIR" || echo_error_exit
}

main() {
    #install_openssl
    install_curl
    install_libzmq
    install_libevent
    #install_system_packages
    #install_hiredis
    install_mongodbcdriver
    install_mongodbcxxdriver
    install_qhetu
    install_Qpanda2
	install_Qpanda3
	echo_to_terminal "所有依赖包安装完成！"
	
    #cd "$SCRIPT_DIR" # 切换到build.sh所在目录编译司南
    #install_politos
    exit 0
}

main

