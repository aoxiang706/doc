---
name: agx-cpp-engineering
description: AGX/ptz100_agx 仓库 C++ 工程规范与现代社区编程实践。修改或新增 C++ 代码（.cpp/.h/.hpp、CMake、ROS2 C++ 节点、alink、ptz、video 等模块）前必读并严格执行。用户未另指定时以本规范为准。
---

# C++ 工程规范与开发经验（AGX 通用）

> 长期维护大型 C++ 代码库的通用实践（服务端 / 系统 / 嵌入式）。  
> 原则：**代码是写给人读的，顺便给编译器执行。** 风格：**现代简洁**。

**开发前必读**：修改 AGX（ptz100_agx）C++ 代码前先通读本规范；用户未另指定时以本规范为准。

**流程**：读规范 → 看所在模块已有写法（冲突时新代码优先本规范）→ 编码 → 文末自检。

---

## 一、现代简洁风格（核心）

- **可读**：写法直白，避免晦涩技巧和隐式副作用。  
- **简洁**：用尽量少的代码把意图说清楚，不做无用抽象。  
- **内聚**：一个类只管一类事；实现细节放进 `.cpp`，头文件少暴露。  
- **显式、安全、小步**：类型、所有权、错误语义写清楚；先正确再优化；一次改动只解决一个问题。

---

## 二、命名

- **见名知意**；类型名大驼峰；函数名用动词短语；常量 `k` 前缀或宏全大写；`.h` 与 `.cpp` 成对。
- **局部变量、参数**：小写加下划线（推荐）或小驼峰，同一模块内统一，**不加尾下划线**。
- **成员变量**：默认 **尾下划线**（如 `pool_size_`）。若该文件所在模块**历来统一**用 `m_` 前缀（如 `m_pool_size`），可继续沿用，**同一类内禁止两种风格混用**。

```cpp
class Pool {
    std::size_t size_{};              // 成员：尾下划线
    bool acquire(int32_t timeout_ms); // 参数 / 局部：不加尾下划线
};
```

---

## 三、类型与初始化

- **定义即初始化（必须）**：禁止读取可能未赋值的变量。标量零值 **`T x{}`**；非零或有业务含义写 **`T x{值}`**；指针 **`T* p{nullptr}`**；成员在类内 `{}` 或构造函数初始化列表写全。
- **不变量、只读参数加 `const`**。
- **固定位宽整数**：协议、序列化、跨平台接口、结构体字段用 `int32_t`、`uint32_t`、`int64_t`、`uint64_t` 等（头文件 `<cstdint>`）；**禁止**用裸 `int`、`long`、`unsigned` 作为对外约定。仅本函数内的小循环下标可用 `int`；与容器 `.size()` 比较用 **`std::size_t`**。
- 新代码优先 **`enum class` 强类型枚举**；用 **`bool`** 表示真假；可选值用 **`std::optional`**；**`auto`** 不用于掩盖接口或协议里的关键类型。
- 向容器追加用 **`emplace_back`**；预知大小时 **`reserve`**（见第十二节）；避免在循环里反复拼接字符串。

```cpp
#include <cstdint>

// ❌ 裸 int + 未初始化
struct Header { int version; unsigned id; };
int32_t count;
if (ok) { count = 1; }

// ✅ 固定位宽 + {}
struct Header { int32_t version{}; uint32_t packet_id{}; };
int32_t count{};
int32_t retry_limit{3};
Foo* ptr{nullptr};
std::vector<Item> items{};
```

---

## 四、比较与分支

- 与字面量、常量比较时：**常量在左**（`nullptr == ptr`、`0 == rc`）。
- 先处理错误和边界再写主流程（**早返回**）；`switch` 分支写全，`default` 要有兜底。

```cpp
// ❌ 嵌套                    // ✅ 早返回
Error f(Request* r) {         Error f(const Request& r) {
  if (r && r->valid())          if (!r.valid()) return Error::kInvalid;
    return work(*r);            return work(r);
  return Error::kInvalid;     }
}

switch (state) {
  case State::kIdle:   return handleIdle();
  case State::kActive: return handleActive();
  default:             return Error::kUnexpected;
}
```

---

## 五、函数

- 一个函数只做一件事；输入用 `const T&` 或小的值类型；输出参数放最后。
- 统一错误返回方式；**禁止忽略返回值**；禁止未说明含义的特殊返回值（如 `-999`）；参数过多时收成配置结构体。

```cpp
parseJson(text);                              // ❌ 忽略返回值
if (auto rc = parseJson(text); !rc.ok())      // ✅
  return rc;
bool loadConfig(const std::string& path, Config* out);
```

---

## 六、资源与所有权

- 优先栈对象和 `unique_ptr`；确需共享再用 `shared_ptr`；**禁止**裸 `new` / `delete`。
- 文件、锁、线程、套接字等：封装成类，析构时自动释放；不需要拷贝的类应禁止拷贝。

```cpp
auto buf = std::make_unique<std::byte[]>(size);  // ✅
class FileGuard {
  explicit FileGuard(int fd) : fd_(fd) {}
  ~FileGuard() { if (0 <= fd_) ::close(fd_); }
  FileGuard(const FileGuard&) = delete;
  int fd_{-1};
};
```

---

## 七、头文件与编译

- 头文件能单独编译、依赖尽量少；能前向声明就不 include 大文件；**禁止**在头文件里 `using namespace std;`。
- 仅本文件使用的辅助函数放在 `.cpp` 的匿名命名空间；对外接口薄，逻辑在 `.cpp`。

```cpp
// Foo.h
class Foo { public: bool parse(std::string_view in); };
// Foo.cpp
namespace { int parseField(std::string_view s) { /*...*/ } }
```

---

## 八、错误处理

- **禁止吞掉错误**、空的 `catch (...)`；失败时打日志、向上返回，资源靠析构释放。
- 项目内异常与错误码风格保持一致；与 C 接口交接处常用错误码；前置条件显式检查，不依赖未定义行为。

```cpp
try { connect(); } catch (...) {}           // ❌
try { connect(); }                           // ✅
catch (const std::exception& e) {
  LOG(ERROR) << e.what(); return Error::kConnectFailed;
}
```

---

## 九、并发

- 共享数据必须加锁或使用原子变量；锁的范围尽量小；持锁期间不做阻塞 IO 或调用户回调。
- 明确哪个线程访问哪个对象；跨线程用队列或任务执行器传递工作。
- 停止线程：设退出标志 → 唤醒 → **`join()` 等待结束**，不要 `detach` 后不管。

```cpp
class Worker {
  std::atomic<bool> stop_{};
  std::thread thread_;
  void loop() { while (!stop_.load()) { /*...*/ } }
public:
  void start() { thread_ = std::thread([this] { loop(); }); }
  void stop() { stop_ = true; if (thread_.joinable()) thread_.join(); }
};
```

---

## 十、日志与注释

- 出错必须打日志；包含模块、操作、关键参数、错误码。注释说明**为什么**，少复述代码在做什么。公共接口写清是否线程安全、是否阻塞、失败时如何返回。

---

## 十一、现代 C++ 补充

- 空指针用 **`nullptr`**，不用 `NULL`；重写虚函数加 **`override`**；多态基类析构函数设为 **`virtual`**。
- 编译期常量用 **`constexpr`**；对象 move 之后不再使用。
- 慎用：宏（除头文件保护、平台相关）、多重继承、友元、全局可变状态。

```cpp
struct Handler final : Base {
  void onEvent() override { /*...*/ }
};
std::optional<User> findUser(uint64_t id);
if (auto u = findUser(id)) notify(*u);
```

---

## 十二、性能

- 先保证正确，再凭性能分析工具找热点，不凭感觉微优化。
- 循环里少拼接字符串（可先 `reserve` 再 `append`）；只读字符串参数用 **`string_view`**；输入传 `const&`，输出可移动。

```cpp
std::string out; out.reserve(total);
for (const auto& p : parts) out.append(p);
void log(std::string_view msg);
```

---

## 十三、审查、反模式与自检

**审查常抓**：未初始化；接口用裸 `int`；忽略返回值；内存泄漏、释放后仍访问；错误路径遗漏；线程安全；成员 `m_` 与尾下划线混用；头文件依赖过多。

**反模式**：仅为一个调用点再包一层类；继承层次过深；滥用全局单例；用异常控制正常流程；「先声明，后面总会赋值」。

**提交前自检**：

- [ ] 变量、成员已 `{}` 初始化？成员默认尾下划线？对外接口用固定位宽整数？
- [ ] 返回值与失败路径已处理？资源、线程能正常退出？
- [ ] 可读、够短、本次改动只做一件事？
