# oyc (O'Young C)

##### 简单的类C脚本语言（使用python3.6+）

/compiler - 编译器

/vm - 基于寄存器的虚拟机

## 语法

### 表达式

```
/********** test.oyc **********/
// 空值
auto n = null;

// 布尔值
auto b = true && (2 > 1) || false;

// 整型
auto i = 1 + (2 * 3 / 4) << 5; // 参照c语言运算符

// 浮点
auto f = 9.9;

// 字符串
auto s = "abc" + "edf";

// 数组
auto arr = [] {0, 1, null, 3, [2] = 2, [4] = 4};

// 字典（映射）
auto st = struct {
  .field1 = "v1",
  ["field2"] = "v2",
  [3] = 3,
};

// 闭包（高阶函数）
auto fn = (auto x, auto y) {
    return x > y ? x : y;
};

trace("n", "type:", typeof(n), "value:", n);
trace("b", "type:", typeof(b), "value:", b);
trace("i", "type:", typeof(i), "value:", i);
trace("f", "type:", typeof(f), "value:", f);
trace("s", "type:", typeof(s), "value:", s);
trace("arr", "type:", typeof(arr), "value:", arr);
trace("st", "type:", typeof(st), "value:", st);
trace("fn", "type:", typeof(fn), "fn(1, 2) value:", fn(1, 2));
```

 输出

```
❯ python3 oyc.py test.oyc
"n" "type:" "null" "value:" null
"b" "type:" "bool" "value:" true
"i" "type:" "int" "value:" 64
"f" "type:" "float" "value:" 9.9
"s" "type:" "str" "value:" "abcedf"
"arr" "type:" "array" "value:" [] {0, 1, 2, 3, 4}
"st" "type:" "struct" "value:" struct {["field1"] = "v1", ["field2"] = "v2", [3] = 3}
"fn" "type:" "closure" "fn(1, 2) value:" 2
```

### 类型转换

```
/********** test.oyc **********/
auto a = 1.1;
auto b = int(a);
auto c = float(b) / 2;
auto d = str(100);
auto e = int(d);
auto f = float(d + ".1");
auto g = bool(f);
trace(a, b, c, d, e, f, g);
```

输出

```
❯ python3 oyc.py test.oyc
1.1 1 0.5 "100" 100 100.1 true
```

### 数组

```
/********** test.oyc **********/
auto arr = [] {0,1,2,3};

// 添加元素到数组
arr[sizeof(arr)] = 4; // sizeof运算符返回当前数组长度
arr[sizeof(arr)] = 5;
trace("output1:", arr);

// 截断数组
delete arr[3]; // 删除索引3以及其后的元素
trace("output2:", arr);
```

输出

```
❯ python3 oyc.py test.oyc
"output1:" [] {0, 1, 2, 3, 4, 5}
"output2:" [] {0, 1, 2}
```

### 字典

```
/********** test.oyc **********/
 auto st = struct {
   .foo = 1,
   .bar = 2,
 };

// 测试字典项是否存在
trace("output1:", typeof(st.haha) == "void");

// 加入字典项
st.haha = "^_^";
trace("output2:", st);

// 删除字典项
delete st.foo;
trace("output2:", st);
```

输出

```
❯ python3 oyc.py test.oyc    :
"output1:" true
"output2:" struct {["foo"] = 1, ["bar"] = 2, ["haha"] = "^_^"}
"output2:" struct {["bar"] = 2, ["haha"] = "^_^"}
```

### 语句

```
/********** test.oyc **********/
if (true) {
  trace("1");
} else {
  trace("2");
}
if (auto x=1; x > 0) // `auto x=1;` 为可选的初始化项
  trace("3");

// while语句
auto n=3;
while (--n >= 1) {
  trace("4");
}

// do...while语句
auto i = 0;
do {
  trace("5");
} while (i++ < 2);

// for语句
for (auto x = 0; x < 3; ++x) {
  trace("6");
}

// foreach语句（遍历数组）
foreach (auto i, v : [] {1,2,3}) {
  trace("7", i, v);
}

// foreach语句（遍历字典）
foreach (auto k, v : struct {.a = 0, .b = 1, .c = 2}) {
  trace("8", k, v);
}

// switch语句
switch (auto c = "b"; c) {
case "a":
  trace("9a");
case "b":
  trace("9b");
case "c":
  trace("9c");
  break;
default:
  trace("9d");
}
```

输出

```
❯ python3 oyc.py test.oyc
"1"
"3"
"4"
"4"
"5"
"5"
"5"
"6"
"6"
"6"
"7" 0 1
"7" 1 2
"7" 2 3
"8" "a" 0
"8" "b" 1
"8" "c" 2
"9b"
"9c"
```

### require

```
/********** test1.oyc **********/
trace("test1's argv:", argv); // argv为命令行参数
auto x = require("test2.oyc", "hi", "hello");
trace("x=", x);

/********** test2.oyc **********/
trace("test2's argv:", argv); // argv为require处传入的参数
return argv[0] + argv[1]; // return将返回到require，即x
```

输出

```
❯ python3 oyc.py test1.oyc x y z
"test1's argv:" [] {"x", "y", "z"}
"test2's argv:" [] {"hi", "hello"}
"x=" "hihello"
```

