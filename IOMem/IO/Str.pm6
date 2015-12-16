#
# Read and write memory objects

use IO::Mem;

class IO::Str is IO::Mem {
    # Return the length of $!source
    method sourcelen(IO::Str:D:) { (self.source or "").chars; }
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

# vim: ft=perl6 expandtab sw=4 softtabstop=4 ai
