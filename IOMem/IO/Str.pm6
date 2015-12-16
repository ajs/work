#
# Read and write memory objects

use IO::Mem;

class IO::Str is IO::Mem {

    has $.basetype = Str;

    multi submethod BUILD(
      Str :$source! is rw,
      :$chomp,
      :$nl-in,
      :$nl-out,
      :$enc,
      :$mode) {
        self.clearsource(Str) if not self.source.defined;
        self;
    }

    multi submethod BUILD(
      :$source,
      :$chomp,
      :$nl-in,
      :$nl-out,
      :$enc,
      :$mode) {
        self.clearsource(Str) if not self.source.defined;
        self;
    }

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

    multi method lines(IO::Str:D: $limit) { }
    multi method lines(IO::Str:D: :$close) {
        gather loop {
            my $line = self.get;
            last if not $line.defined;
            take $line;
        }
    }

    multi method slurp-rest(IO::Str:D: :$bin!) returns Buf {
        Buf.new(self.takerest.comb.map(-> $_ {.ord}));
    }
    multi method slurp-rest(IO::Str:D: :$enc) returns Str {
        if $enc.defined {
            die "slurp-rest(:enc) unsupported";
        }
        return self.takerest;
    }

    method read(IO::Str:D: Int(Cool:D) $bytes) {
        die "Unimplemented: read";
    }
    
    method readchars(Int(Cool:D) $chars = 65536) {
        return self.takepart($chars);
    }

    method Supply(IO::Str :$size = 65536, :$bin --> Supply:D) {
        die "Unsupported :\$bin" if $bin;
        supply {
            my $str = self.readchars($size);
            while $str.chars {
                emit $str;
                $str = self.readchars($size);
            }
            done;
        }
    }

    method write(IO::Str:D: Blob:D $buf) {
        self.print($buf.decode(:enc(self.enc)));
    }

    multi method print(IO::Str:D: Str:D \x) {
        my Str $source := self.source;
        try {
            $source.substr-rw(self.pos) = x;
            CATCH { default { $source.BUILD(:value($source ~ x)) } }
        }
        self.pos = $source.chars;
        True;
    }
    multi method print(IO::Str:D: *@list is raw) {
        self.print(.Str) for @list;
    }
    multi method put(IO::Str:D: Str:D \x) {
        self.print(x);
        self.print-nl;
    }
    multi method put(IO::Str:D: *@list is raw) {
        self.print(.Str) for @list;
        self.print-nl;
    }

    multi method say(IO::Str:D: |c) {
        my @tmp = |c;
        self.print: @tmp.shift.gist while @tmp;
        self.print-nl;
    }
}

# vim: ft=perl6 expandtab sw=4 softtabstop=4 ai
