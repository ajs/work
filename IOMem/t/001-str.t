use v6;

use lib 'lib';
use Test;

plan 2;

use-ok "IO::Str";

use IO::Str;
subtest {
    plan 15;

    my $sio = IO::Str.new(:source("Line1\nLine2\nLine3\n"));
    ok($sio, "Instantiation");
    ok($sio.tell == 0, "tell at start");
    ok($sio.opened, "opened at start");
    ok(not $sio.eof, "not eof at start");
    my @lines_exp = "Line1", "Line2", "Line3";
    for $sio.lines Z 0..* -> ($line, $lineno) {
        my $exp = @lines_exp[$lineno];
        ok($line ~~ $exp, "expected {$lineno}: {$exp.perl}");
    }
    ok($sio.tell == $sio.source.chars, "At end of file");
    ok($sio.opened, "opened at end");
    ok($sio.eof, "end of file at end");
    $sio = IO::Str.new(:source("Line1\nLine2\n\nLine3"), :chomp(False));
    ok($sio, "Second IO::Str");
    ok($sio.get ~~ "Line1\n", "Fist line unchomped");
    ok($sio.slurp-rest ~~ "Line2\n\nLine3", "slurp-rest");
    ok($sio.seek(0, SeekType::SeekFromBeginning), "seek(0)");
    ok($sio.get ~~ "Line1\n", "Fist line unchomped after seek");
}, "IO::Str reader";

subtest {
    plan 11;

    my Str $target;
    my $sio = IO::Str.new(:source($target));
    ok($sio, "Instantiation");
    ok($sio.tell == 0, "tell at start");
    ok($sio.opened, "opened at start");
    ok($sio.eof, "eof at start");
    ok($sio.say("Line1"), True);
    ok($sio.print("Line2\n"), True);
    ok($sio.tell == $sio.source.chars, "At end of file");
    ok($target ~~ "Line1\nLine2\n", "Wrote two lines to string");
    ok($sio.slurp-rest ~~ "", "slurp-rest at eof");
    ok($sio.seek(0, SeekType::SeekFromBeginning), "seek(0)");
    ok($sio.get ~~ "Line1", "Fist line after seek");
}, "IO::Str writer";

# vim: ft=perl6 expandtab sw=4 softtabstop=4 ai
