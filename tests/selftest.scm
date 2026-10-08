; 自测程序：逐条覆盖 spec §4/§5/§8/§9 的规则与边界情况。
; 每行注释给出期望输出，可与解释器输出逐行核对。

; ---- §4.1 quote：原样返回，数据转成点对链 ----
(quote x)                     ; → x
'x                            ; → x
'(1 2 3)                      ; → (1 2 3)
'()                           ; → ()
'(1 (2 3) "s" #t)             ; → (1 (2 3) "s" #t)
'(a . b)                      ; → (a . b)
(car '((1 2) 3))              ; → (1 2)

; ---- §4.2 if：只走一个分支，缺省假分支不打印 ----
(if (> 3 2) 'yes 'no)         ; → yes
(if #f 'bad 'good)            ; → good
(if #f 'bad)                  ; → （无输出）
(if 0 'zero-is-true 'no)      ; → zero-is-true
(if '() 'nil-is-true 'no)     ; → nil-is-true
(if "" 'empty-string-true 'no); → empty-string-true

; ---- §4.3 cond ----
(cond ((= 1 2) 'a) ((= 2 2) 'b) (else 'c))   ; → b
(cond (else 'd))                             ; → d
(cond ((> 2 3)) (else 42))                   ; → 42
(cond ((> 2 3) 'x))                          ; → （无输出，全部不匹配）
(cond (#f 1) (5))                            ; → 5（子句无表达式时返回测试值）

; ---- §4.4 and / or：短路 ----
(and)                         ; → #t
(or)                          ; → #f
(and 1 2 3)                   ; → 3
(or #f #f 7)                  ; → 7
(and 1 #f (/ 1 0))            ; → #f（后面的不执行）
(or #f 2 (/ 1 0))             ; → 2（后面的不执行）
(not 0)                       ; → #f（只有 #f 是假）

; ---- §4.5 define ----
(define pi 3)                 ; → pi
pi                            ; → 3
(define (square x) (* x x))   ; → square
(square 7)                    ; → 49
(define identity (lambda (x) x))  ; → identity
(identity 'ok)                ; → ok

; ---- §4.6 lambda / 闭包 ----
((lambda (x) (* x 2)) 5)      ; → 10
((lambda (a b) (- a b)) 10 4) ; → 6
(define (make-adder n) (lambda (x) (+ x n)))  ; → make-adder
(define add7 (make-adder 7))  ; → add7
(add7 5)                      ; → 12
((make-adder 100) 1)          ; → 101

; ---- §4.7 let：并行绑定 ----
(let ((x 3) (y 4)) (+ x y))                 ; → 7
(let ((x 1) (x 2)) x)                       ; → 2（同名绑定，后者生效）
(let ((a 1)) (let ((b (+ a 1))) (* a b)))   ; → 2（内层可见外层）
(define x 50)                               ; → x
(let ((x 1)) x)                             ; → 1（let 不污染外层）
x                                           ; → 50
(let ((f (lambda (n) (* n n)))) (f 9))      ; → 81

; ---- §4.8 begin ----
(begin (define z 1) (+ z 41)) ; → 42
(begin 1 2 3)                 ; → 3
(begin)                       ; → （无输出）

; ---- §5 算术 ----
(+ 1 2 3)                     ; → 6
(+)                           ; → 0
(*)                           ; → 1
(- 10 4 1)                    ; → 5
(- 5)                         ; → -5
(* 2 3 4)                     ; → 24
(/ 7 2)                       ; → 3
(/ -7 2)                      ; → -3
(/ 7 -2)                      ; → -3
(/ -7 -2)                     ; → 3
(/ 2)                         ; → 0.5
(/ 1 4)                       ; → 0
(/ 1 2 3)                     ; → 0
(modulo 17 5)                 ; → 2
(modulo -7 2)                 ; → 1
(quotient 17 5)               ; → 3
(quotient -7 2)               ; → -3
(expt 2 10)                   ; → 1024
(expt 2 0)                    ; → 1
(expt 2 -1)                   ; → 0.5
(abs (- 5 9))                 ; → 4
(abs -4)                      ; → 4

; ---- §5 比较：链式，支持数字与符号 ----
(= 1 1)                       ; → #t
(= 1 1 1)                     ; → #t
(= 1 2)                       ; → #f
(= 'a 'a)                     ; → #t
(= 'a 'b)                     ; → #f
(< 2 3 4)                     ; → #t
(< 2 4 3)                     ; → #f
(> 5 5)                       ; → #f
(>= 6 5)                      ; → #t
(<= 4 4)                      ; → #t

; ---- §5 列表：点对链 ----
(cons 1 2)                    ; → (1 . 2)
(cons 1 '(2 3))               ; → (1 2 3)
(cons '(1) '(2))              ; → ((1) 2)
(car '(1 2 3))                ; → 1
(cdr '(1 2 3))                ; → (2 3)
(car (cons 1 2))              ; → 1
(cdr (cons 1 2))              ; → 2
(list)                        ; → ()
(list 1 2 3)                  ; → (1 2 3)
(length '(a b c d))           ; → 4
(length '())                  ; → 0
(append '(1 2) '(3 4))        ; → (1 2 3 4)
(append)                      ; → ()
(append '(1) '(2) '(3))       ; → (1 2 3)
(append '() '(1))             ; → (1)
(null? '())                   ; → #t
(null? '(1))                  ; → #f
(pair? '(1 2))                ; → #t
(pair? '())                   ; → #f
(pair? (cons 1 2))            ; → #t
(list? '(1 2))                ; → #t
(list? (cons 1 2))            ; → #f
(list? '())                   ; → #t

; ---- §5 谓词 ----
(number? 5)                   ; → #t
(number? 'x)                  ; → #f
(number? #t)                  ; → #f
(boolean? #t)                 ; → #t
(boolean? 1)                  ; → #f
(symbol? 'x)                  ; → #t
(symbol? "x")                 ; → #f
(string? "s")                 ; → #t
(string? 's)                  ; → #f
(procedure? car)              ; → #t
(procedure? (lambda (x) x))   ; → #t
(procedure? 1)                ; → #f
(zero? 0)                     ; → #t
(even? 8)                     ; → #t
(odd? 7)                      ; → #t
(eq? 'a 'a)                   ; → #t
(eq? 1 1)                     ; → #t
(eq? '() '())                 ; → #t
(eq? '(1) '(1))               ; → #f
(eq? #t 1)                    ; → #f
(equal? '(1 2 3) (list 1 2 3)); → #t
(equal? '(1 (2)) '(1 (2)))    ; → #t
(equal? '(1) '(2))            ; → #f
(equal? 'x 'x)                ; → #t
(equal? 'a "a")               ; → #f
(equal? #t 1)                 ; → #f
(equal? 1 1)                  ; → #t

; ---- §8 值的打印 ----
42                            ; → 42
-7                            ; → -7
#t                            ; → #t
#f                            ; → #f
'foo                          ; → foo
"hello"                       ; → "hello"
"tab\there"                   ; → "tab\there"
0.5                           ; → 0.5
'(1 2 3)                      ; → (1 2 3)
'(1 . 2)                      ; → (1 . 2)
'((1 2) . 3)                  ; → ((1 2) . 3)
'()                           ; → ()
car                           ; → #<procedure>
(lambda (x) x)                ; → #<procedure>

; ---- §9 词法作用域 ----
(define (counter-from n) (lambda () n))  ; → counter-from
(define c5 (counter-from 5))             ; → c5
(c5)                                     ; → 5
(define n 99)                            ; → n
(c5)                                     ; → 5（闭包记住定义时的 n）

; ---- 递归（§7）----
(define (fact n) (if (= n 0) 1 (* n (fact (- n 1)))))  ; → fact
(fact 10)                                              ; → 3628800
(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))  ; → fib
(fib 15)                                               ; → 610
(define (map f xs) (if (null? xs) '() (cons (f (car xs)) (map f (cdr xs)))))  ; → map
(map (lambda (x) (* x x)) '(1 2 3 4))                  ; → (1 4 9 16)
(define (filter pred xs)
  (cond ((null? xs) '())
        ((pred (car xs)) (cons (car xs) (filter pred (cdr xs))))
        (else (filter pred (cdr xs)))))                ; → filter
(filter (lambda (x) (> x 3)) '(1 5 2 6 3 7))           ; → (5 6 7)

; ---- §5 display / newline（结果为无值，不打印）----
(display "no quotes")         ; 打印 no quotes（不换行）
(newline)                     ; 打印换行
(display '(1 (2) "s"))        ; 打印 (1 (2) "s")
(newline)
(display 42)                  ; 打印 42
(newline)
(display #t)                  ; 打印 #t
(newline)
