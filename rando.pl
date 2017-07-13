#!/usr/bin/env perl
#
# Generate random lines of "working" Perl code.

use v5.20;
use feature qw(signatures);
no warnings qw(experimental::signatures);
#use encoding 'utf8';

use Getopt::Long qw(GetOptionsFromArray);
use Pod::Usage;
use IPC::Open3;

# Used to time out subprocess
use Time::Out qw(timeout);
# Used to constrain the random code from affecting the system.
use Safe;
# Used to select characters for the code.
use List::Util::WeightedChoice qw(choose_weighted);

# Output buffering off.
$|=1;
# The operations that should not affect the external system
our @SAFE_MASK = qw(:base_core :base_loop :base_orig :base_mem);

my $options = command_line(@ARGV);
my $randlen = $options->{maxlen} - $options->{minlen};
my $baselen = $options->{minlen};
# Safe seems to spew to STDERR no matter what we do, so
# turn it off.
if (not $options->{stderr}) {
    open(STDERR, ">", "/dev/null") or die "STDERR: $!";
}
my $info = sub { say @_ if not $options->{quiet} };
my $latin = $options->{latin};

if ($latin) {
    binmode STDOUT, ":utf8";
}

# Main loop
my $trials = 0;
for(my $i=0;$i<$options->{count};$i++) {
    for(my $n = 1;;$n++) {
        my $found = 0;
        timeout $options->{timeout} => sub {
            my $code = randcodish(
                int(rand($randlen)+$baselen),
                $options->{comments},
                $latin);
            # If this sets $@, the code was invalid
            jail($code, $options->{strict});
            if (! $@) {
                if ($options->{deparse}) {
                    (my $dpc = deparsed($code, $latin)) =~ s/\s+\z//;
                    say $dpc;
                } elsif ($options->{quiet}) {
                    say $code;
                } else {
                    say "after $n attempts: $code";
                    say "Deparsed: ", deparsed($code, $latin);
                }
                $trials += $n;
                # Would be "last" if we were not in a sub
                $found = 1;
                return
            } else {
                if ($options->{verbose}) {
                    say "Exit $@ from $code" if $@;
                }
            }
        };
        die $@ if $@;
        last if $found;
    }
}
my $perl = ($options->{strict}?'strict ':'') . 'perl';
$info->("$options->{count} of $trials random strings are valid $perl");
$info->(sprintf("%.5f%%", ($options->{count}/$trials)*100));
exit 0;

sub deparsed($code, $timeout = 5, $latin = 0) {
    my $dp_code;

    timeout $timeout => sub {
        my @latin = ($latin ? '-C' : ());
        my $pid = open3(
            my $input, my $output, 0, 'perl', @latin, '-MO=Deparse', '-');
        if ($latin) {
            binmode($input, ":utf8");
            binmode($output, ":utf8");
        }
        say $input $code;
        close $input;
        $dp_code = join('', grep {!/syntax OK/} <$output>);
        close $output;
        waitpid($pid, 0);
    };
    die $@ if $@;

    return $dp_code;
}

sub weights($comments = 0, $filter = undef, $latin = 0) {
    # Return an ARRAY of two ARRAYS containing
    # the keys and values of the weights to be used
    # in selecting characters for output.
    my %weights = ();

    my @ident = ('a'..'z', 'A'..'Z', '_');
    push @ident, grep {/\w/} map {chr;} 128..255 if $latin;
    my @num = (0..9);
    my @punct = (map {chr($_)} 33..47, 58..64, 91..96, 123..126);

    my $filter_func = ($filter ? $filter : ($comments ? sub {1;} : sub { $_[0] ne '#' }));
    my @all = grep {$filter_func->($_)} @punct, @num, @ident, ' ';

    my $weight = 1;
    @weights{@all} = map {$weight} @all;

    my $keyword_weight = 3;
    $weights{';'} = $keyword_weight;
    #$weights{';my '} = $keyword_weight;
    #$weights{';while ('} = $keyword_weight;
    #$weights{';if ('} = $keyword_weight;
    #$weights{';for '} = $keyword_weight;
    #$weights{';sub '} = $keyword_weight;

    return [[keys %weights], [values %weights]];
}

sub randcodish($len = 1024, $comments = 0, $latin = 0) {
    # Using the weights return a string of potential code $len long
    state $weight_info = weights($comments, undef, $latin);
    return join('', map {choose_weighted(@$weight_info)} 1..$len);
}

sub jail($code, $strict = 1) {
    # Run the code in a safe environment and set $@ if it fails
    my $jail = new Safe;
    $jail->permit_only(@SAFE_MASK);
    $jail->reval($code, $strict);
}

sub command_line(@args) {
    my %options = (
        help => 0,
        man => 0,
        quiet => 0,
        verbose => 0,
        deparse => 0,
        count => 1,
        strict => 1,
        comments => 0,
        latin => 0,
        timeout => 5,
        maxlen => 75,
        minlen => 15,
        stderr => 0
    );

    GetOptionsFromArray(
        \@args,
        'help|?'      => \$options{help},
        'man'         => \$options{man},
        'stderr'      => sub { $options{stderr} = 1 },
        'quiet|q'     => \$options{quiet},
        'verbose|v'   => \$options{verbose},
        'deparse'     => \$options{deparse},
        'non-strict'  => sub { $options{strict} = 0 },
        'comments'    => \$options{comments},
        'latin'       => \$options{latin},
        'timeout=i'   => \$options{deparse_timeout},
        'count|n=i'   => \$options{count},
        'maxlen=i'    => \$options{maxlen},
        'minlen=i'    => \$options{minlen}) or pod2usage(2);

    pod2usage(-exitval => 0) if $options{help};
    pod2usage(-exitval => 0, -verbose => 2) if $options{man};

    pod2usage("Extra command line arguments") if @args;

    return \%options;
}

1;
__END__

=head1 NAME

rando - Generate random Perl code

=head1 SYNOPSIS

    rando
        [--help] [--man] [--quiet|-q] [--verbose|-v] [--stderr]
        [--deparse] [--comments] [--non-strict] [--count|-n <n>]
        [--latin] [--maxlen n] [--minlen n] [--timeout <n>]

    --help - Produce help text
    --man - Produce manual
    -q
    --quiet - Do not print verbose statistics
    -v
    --verbose - Print all error messages for failed code
    --stderr - Do not shut down stderr (warning, messy)
    --deparse - Only print the deparsed version.
    --comments - Include comments in generated code.
    --non-strict - Do not require program to work under 'use strict'
    --latin - Include latin identifier characters
    -n <n>
    --count <n> - Number of programs to generate
    --maxlen <n> - Max length of program (default=75)
    --minlen <n> - Min length of program (default=15)
    --timeout <n> - Time out any given code check after n sec (default=5)

=head1 AUTHOR

By Aaron Sherman <ajs@ajs.com>, (c) 2017

=head1 LICENSE

This program is distributed under the same terms as Perl itself.

=cut

# vim: ft=perl sw=4 sts=4 ai et
