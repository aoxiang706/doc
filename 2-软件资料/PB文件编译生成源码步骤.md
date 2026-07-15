#一、安装编译环境

# 1. 更新包列表
sudo apt update

# 2. 安装 protobuf 编译器（从 apt 仓库）
sudo apt install protobuf-compiler

# 3. 安装 nanopb 及其依赖
sudo apt install python3-pip python3-protobuf
pip3 install nanopb

# 4. 验证安装i
# 清除 shell 的命令路径缓存
hash -r

which protoc
# 应该输出: /usr/bin/protoc

protoc --version
# 应该输出版本号（可能比 3.20.3 更新或更旧，取决于 Ubuntu 版本）

which nanopb_generator
# 应该输出: /usr/bin/nanopb_generator

# 5. 编译生成文件示例（TracerMatrix目录下有：TracerMatrix.proto、TracerMatrix.options）
cd TracerMatrix
nanopb_generator TracerMatrix.proto
