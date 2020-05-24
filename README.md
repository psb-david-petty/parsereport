# parsereport
Parse [Codecheck.it](http://codecheck.it/) report, comment on it, and e-mail the author.

The `data/codecheck-*.signed.zip` files in this repository are all solutions to [http://codecheck.it/files/2003300209dlfnv31cvbxfv5uie44bq0jqo](http://codecheck.it/files/2003300209dlfnv31cvbxfv5uie44bq0jqo).

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

<h2 style="color: blue;">TODO</h2>

- Document [Codecheck.it](http://codecheck.it/) and the `report.html` file more completely.
- Document external programs used: [MacDown](https://macdown.uranusjr.com/) and [`jarsigner`](https://docs.oracle.com/javase/7/docs/technotes/tools/windows/jarsigner.html).
- Potentially add options for specifying locations of markdown editor &amp; [`jarsigner`](https://docs.oracle.com/javase/7/docs/technotes/tools/windows/jarsigner.html).
- Potentially add options for SMTP server &amp; port (currently "smtp.gmail.com" &amp; 465).

<hr>

[&#128279; permalink](https://psb-david-petty.github.io/parsereport) and [&#128297; repository](https://github.com/psb-david-petty/parsereport) for this page.
