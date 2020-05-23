# parsereport
Parse [Codecheck.it](http://codecheck.it/) report, comment on it, and e-mail the author.

## Sample use
<pre>
$ <strong style="color: green;">python3 src/parsereport.py -?</strong>
usage: parsereport.py [-?] [--version] [-e ADDR] [-p PASS] [-r] [-v] PATH

Read .SIGNED.ZIP files from PATH, parse report for e-mail address and code,

positional arguments:
  PATH                      path to directory with .SIGNED.ZIP files

optional arguments:
  -?, --help                show this help message and exit
  --version                 show program's version number and exit
  -e ADDR, --email ADDR     SMTP e-mail (default: None)
  -p PASS, --password PASS  SMTP password (default: None)
  -r, --resend              resend comment, if available (default: False)
  -v, --verbose             echo status information (default: False)
</pre>

<hr>

[&#128279; permalink](https://psb-david-petty.github.io/parsereport) and [&#128297; repository](https://github.com/psb-david-petty/parsereport) for this page.
