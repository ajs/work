#
# Read and write memory objects

class IO::Mem is IO::Handle {
    has $.source;
    has $.pos is rw = 0; # only subclasses should write to this
    has $.opened = True;
    has $.chomp is rw = Bool::True;
    has $.nl-in = ["\x0A", "\r\n"];
    has Str:D $.nl-out is rw = "\n";
    has $!enc;
    has $.mode;

    method open(IO::Mem:D:
      :$r, :$w, :$a, :$update,
      :$rw, :$ra,
      :$mode is copy,
      :$create is copy,
      :$append is copy,
      :$truncate is copy,
      :$exclusive is copy,
      :$bin,
      :$chomp = True,
      :$enc   = Nil,
      :$nl-in is copy = ["\x0A", "\r\n"],
      Str:D :$nl-out is copy = "\n",
    ) {
        $mode //= do {
            when so ($r && $w) || $rw { $create              = True; 'rw' }
            when so ($r && $a) || $ra { $create = $append    = True; 'rw' }

            when so $r { 'ro' }
            when so $w { $create = $truncate  = True; 'wo' }
            when so $a { $create = $append    = True; 'wo' }

            when so $update { 'rw' }

            default { 'ro' }
        }
	if $truncate and not $append {
	    $!source = self.sourcepart(0);
	}
	if $append {
	    $!pos = $!source.chars;
	    CATCH { $!pos = $!source.elems }
	}
	$!mode = $mode;
	$!opened = True;
	self;
    }

    method close(IO::Mem:D: --> True) {
	$!pos = 0;
	$!opened = False;
    }

    # Return the length of $!source
    method sourcelen(IO::Mem:D:) { ... }
    # Return a portion of $!source without advancing $!pos
    method sourcepart(IO::Mem:D: Cool $length) { ... }
    # Return the pos of $what in $!source or undefined
    method sourcefind(IO::Mem:D: Cool $what) { ... }
    # Return a portion of $!source, advancing $!pos
    method takepart(IO::Mem:D: Cool $length) { ... }
    # Return one "line" from $!source
    method get(IO::Mem:D:) { ... }

    method eof(IO::Mem:D:) {
	$!pos == self.sourcelen;
    }

    method getc(IO::Mem:D:) {
	return self.takepart(1);
    }

    proto method comb(|) { * }
    multi method comb(IO::Mem:D: :$close = False) { ... }
    multi method comb(IO::Mem:D: Int:D $size, :$close = False) { ... }
    multi method comb(IO::Mem:D: $comber, :$close = False) { ... }

    proto method split (|) { * }
    multi method split(IO::Mem:D: :$close = False, :$COMB) { ... }
    multi method split(IO::Mem:D: $splitter, :$close = False, :$COMB) { ... }

    proto method words (|) { * }
    multi method words(IO::Mem:D: :$close) { ... }

    proto method lines (|) { * }
    multi method lines(IO::Mem:D: $limit) { ... }
    multi method lines(IO::Mem:D: :$close) { ... }

    method read(IO::Mem:D: Int(Cool:D) $bytes) { ... }
    method readchars(Int(Cool:D) $chars = 65536) { ... }
    method Supply(IO::Mem:D: :$size = 65536, :$bin --> Supply:D) { ... }

    proto method seek(|) { * }
    multi method seek(IO::Mem:D: Int:D $offset, Int:D $whence --> True) {
        die "Use SeekType for whence parameter";
    }
    multi method seek(IO::Mem:D: Int:D $offset, SeekType:D $whence) {
        my $where;
        if $whence == SeekType::SeekFromBeginning {
            $where = $offset;
        } elsif $whence == SeekType::SeekFromCurrent {
            $where = self.pos + $offset;
        } elsif $whence == SeekType::SeekFromEnd {
            $where = self.sourcelen - $offset;
        }
        $!pos = min(self.sourcelen, $where);
        return True;
    }

    method tell(IO::Mem:D:) returns Int { return $!pos }

    method write(IO::Mem:D: Blob:D $buf --> True) { ... }
    method t(IO::Mem:D:) { False; }

    method lock(IO::Mem:D: Int:D $flag) { ... }
    method unlock(IO::Mem:D: --> True) { ... }

    proto method print(|) { * }
    multi method print(IO::Mem:D: str:D \x --> True) { ... }
    multi method print(IO::Mem:D: Str:D \x --> True) { ... }
    multi method print(IO::Mem:D: *@list is raw --> True) { ... }

    method print-nl(IO::Mem:D: --> True) { self.print($!nl-out); }
    multi method say(IO::Mem:D: |c) { self.print(|c); self.print-nl; }

    proto method put(|) { * }
    multi method put(IO::Mem:D: str:D \x --> True) { ... }
    multi method put(IO::Mem:D: Str:D \x --> True) { ... }
    multi method put(IO::Mem:D: *@list is raw --> True) { ... }

    proto method slurp-rest(|) { * }
    multi method slurp-rest(IO::Mem:D: :$bin!) returns Buf { ... }
    multi method slurp-rest(IO::Mem:D: :$enc) returns Str { ... }

    method chmod(IO::Mem:D: Int $mode) { ... }
    method IO(IO::Mem:D: |c) { ... } # TODO probably do this here

    method path(IO::Mem:D:) { Mu; }
    multi method Str(IO::Mem:D:) { $!source.Str }

    multi method perl(IO::Mem:D:) {
	my $me = self.WHAT.perl;
	my $source = $!source.perl;
	my $chomp = $!chomp;
	my $mode = $!mode;

	"{$me}.new(source => {$source}, chomp => {$chomp}, mode => {$mode})";
    }

    method flush(IO::Mem:D: --> True) { True; }
    method encoding(IO::Mem:D: $enc?) {
	if $enc.defined {
	    die "Unimplemented: encoding";
	}
	$!enc;
    }

    method e(IO::Mem:D:) { True; }
    method d(IO::Mem:D:) { False; }
    method f(IO::Mem:D:) { False; }
    method s(IO::Mem:D:) { False; }
    method l(IO::Mem:D:) { False; }
    method r(IO::Mem:D:) { True; }
    method w(IO::Mem:D:) { True; } # TODO - test string for writability
    method x(IO::Mem:D:) { False; }
    method modified(IO::Mem:D:) { now; }
    method accessed(IO::Mem:D:) { now; }
    method changed(IO::Mem:D:)  { now; }

    method watch(IO::Mem:D:) { die "Unimplemented: watch" }
}

class IO::Str is IO::Mem {
    # Return the length of $!source
    method sourcelen(IO::Str:D:) { self.source.chars; }
    # Return a portion of $!source without advancing $!pos
    method sourcepart(IO::Str:D: Cool $length) {
        self.source.substr(self.pos, $length);
    }
    # Return the pos of $what in $!source or undefined
    method sourcefind(IO::Str:D: Cool $what) {
        self.source.index($what, self.pos);
    }
    # Return a portion of $!source, advancing $!pos
    method takepart(IO::Str:D: Cool $length) {
        my $part = self.sourcepart($length);
        self.pos += $length;
        return $part;
    }
    method takerest(IO::Str:D:) {
        return self.source.substr(self.pos);
        LAST { self.pos = self.sourcelen; }
    }
    # Return one "line" from $!source
    method get(IO::Str:D:) {
        return Nil unless self.opened;
        my @endings = |(self.nl-in);
        my $ending = rx{@endings$};
        my $buffer = "";
        my $cread = 0;
        for self.source.substr(self.pos).comb -> $c {
            $cread++;
            $buffer ~= $c;
            self.pos += 1;
            if $buffer ~~ $ending {
                if self.chomp {
                    $buffer.subst-mutate($ending, '');
                }
                return $buffer;
            }
        }
        if $cread == 0 {
            $buffer = Nil;
        }
        return $buffer;
    }

    method getc(IO::Str:D:) {
        return Nil unless self.opened;
        if self.pos < self.source.chars {
            my $c = self.source.substr(self.pos, 1);
            self.pos += 1;
            return $c;
        } else {
            return Nil;
        }
    }

    proto method lines (|) { * }
    multi method lines(IO::Str:D: $limit) { }
    multi method lines(IO::Str:D: :$close) {
        gather loop {
            my $line = self.get;
            last if not $line.defined;
            take $line;
        }
    }

    proto method slurp-rest(|) { * }
    multi method slurp-rest(IO::Str:D: :$bin!) returns Buf {
        Buf.new(self.takerest.comb.map(-> $_ {.ord}));
    }
    multi method slurp-rest(IO::Str:D: :$enc) returns Str {
        if $enc.defined {
            die "slurp-rest(:enc) unsupported";
        }
        return self.takerest;
    }

}

my $sio = IO::Str.new(:source("Line1\nLine2\nLine3\n"));
say "String 1 Start POS: {$sio.tell} OPEN: {$sio.opened} EOF: {$sio.eof}";
for $sio.lines -> $line { say $line.perl; }
say "String 1 End POS: {$sio.tell} OPEN: {$sio.opened} EOF: {$sio.eof}";

$sio = IO::Str.new(:source("Line1\nLine2\n\nLine3"), :chomp(False));
say "String 2 Start POS: {$sio.tell} OPEN: {$sio.opened} EOF: {$sio.eof}";
for $sio.lines -> $line { say $line.perl; }
say "String 2 End POS: {$sio.tell} OPEN: {$sio.opened} EOF: {$sio.eof}";

$sio = IO::Str.new(:source("Line1\nLine2\n\nLine3"), :chomp(False));
say "String 3 from pos=6:";
$sio.seek(6,SeekType::SeekFromBeginning);
say $sio.slurp-rest;

# vim: ft=perl6 expandtab sw=4 softtabstop=4 ai
