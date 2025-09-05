#!/usr/bin/env python3

"""
Filer -- Pattern Matching File Management Utility
Copyright (c) 1976-2020 by Jeff Shrager

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

The GNU General Public License is available at:
   http://www.gnu.org/copyleft/gpl.html

Filer is a filename pattern matcher and rebuilder. The matchpattern is 
compared with the files in the current directory and output to standard out.

***WARNING*** Filer is both very useful and very dangerous. Before
you either pipe the produced commands to a shell for execution, be
absolutely sure that it's going do what you want, or you might end up
making a mess of your directory.
"""

import os
import sys
import argparse
import time
from datetime import datetime

FNLEN = 300  # max length of a filename or rebuilt name

class Filer:
    def __init__(self):
        self.include_dots = False
        self.quotenames = False
        self.table = [[''] * FNLEN for _ in range(10)]
        self.nn = [''] * FNLEN  # holds the resulting name from rebuilding
        self.nnp = 0  # where in the new name are we?
        self.r = ""  # the rebuilding pattern
        self.p = ""  # the match pattern
        self.cmd = ""  # the command, if any
        self.stk = 0  # last *
        self.qmk = 0  # last ?
        self.seq_number = 1  # sequence number counter
        
    def clear_table_line(self, line):
        """Clear a line in the table"""
        for k in range(FNLEN):
            self.table[line][k] = ''
    
    def match(self, fn, p, fp, pp, tp):
        """
        Smart matcher using * (any chars) and ? (any one char).
        Returns True for a good match, False for a bad one.
        """
        if fn.startswith('.') and not self.include_dots:
            return False
            
        while True:
            # If we're at the end of both filename and pattern, we win!
            if fp >= len(fn) and pp >= len(p):
                return True
            
            # If we're out of one or the other, fail!
            if fp >= len(fn) or pp >= len(p):
                return False
            
            # If they're the same letter, still okay, move on through recursion
            if fn[fp] == p[pp]:
                return self.match(fn, p, fp + 1, pp + 1, tp)
            
            # See if the pattern char is a ? -- still okay, but save it!
            elif p[pp] == '?':
                self.clear_table_line(tp)
                self.table[tp][0] = '?'
                self.table[tp][1] = fn[fp]
                return self.match(fn, p, fp + 1, pp + 1, tp + 1)
            
            # See if the pattern char is a * -- still okay, also save it and recurse
            elif p[pp] == '*':
                sp = 1  # set up a local star pointer
                self.clear_table_line(tp)
                self.table[tp][0] = '*'  # Insert marker for *
                
                self.table[tp][sp] = fn[fp]
                if self.match(fn, p, fp + 1, pp + 1, tp + 1):
                    return True
                
                # If we got here then we want to expand the * entry by one
                while True:
                    fp += 1
                    sp += 1
                    if fp >= len(fn):
                        if pp + 1 >= len(p):
                            return True
                        else:
                            return False
                    else:
                        self.table[tp][sp] = fn[fp]
                        if self.match(fn, p, fp + 1, pp + 1, tp + 1):
                            return True
            else:
                return False
    
    def rebuild(self):
        """Rebuild the filename using the pattern and table"""
        self.stk = 0
        self.qmk = 0
        self.nnp = 0
        
        # Clear the output name
        for k in range(FNLEN):
            self.nn[k] = ''
        
        l = 0
        while l < len(self.r):
            if self.r[l] == '*':
                self.rb_star(l)
                l += 1
            elif self.r[l] == '?':
                self.rb_qmark(l)
                l += 1
            elif self.r[l] == "'":
                l = self.rb_quote(l)
            else:
                self.nn[self.nnp] = self.r[l]
                self.nnp += 1
                l += 1
    
    def rb_star(self, l):
        """Handle * in rebuilding pattern"""
        l += 1
        dg = self.get_digit(l)
        
        if dg == 99:
            print("Filer: Pattern index must be 1-9!")
            return
        
        if dg == 0:
            self.stk += 1
            dg = self.stk
        else:
            self.stk = dg
        
        where = 0
        temp_dg = dg
        while temp_dg != 0 and where < 10:
            if self.table[where][0] == '*':
                temp_dg -= 1
            if temp_dg > 0:
                where += 1
        
        if where >= 10 or not self.table[where][0]:
            print("Can't find indexed pattern item.")
            return
        
        self.rb_copy(where)
    
    def rb_qmark(self, l):
        """Handle ? in rebuilding pattern"""
        l += 1
        dg = self.get_digit(l)
        
        if dg == 99:
            print("Filer: Pattern index must be 1-9!")
            return
        
        if dg == 0:
            self.qmk += 1
            dg = self.qmk
        else:
            self.qmk = dg
        
        where = 0
        temp_dg = dg
        while temp_dg != 0 and where < 10:
            if self.table[where][0] == '?':
                temp_dg -= 1
            if temp_dg > 0:
                where += 1
        
        if where >= 10 or not self.table[where][0]:
            print("Can't find indexed pattern item.")
            return
        
        self.rb_copy(where)
    
    def rb_quote(self, l):
        """Handle quote sequences in rebuilding pattern"""
        l += 1
        if l < len(self.r):
            if self.r[l] == 'd':
                return self.rb_date(l)
            elif self.r[l] == 's':
                return self.rb_seq(l)
            else:
                print("Filer: Invalid '_ quote spec!")
                sys.exit(2)
        return l
    
    def rb_date(self, l):
        """Handle date formatting in rebuilding pattern"""
        l += 1
        if l >= len(self.r):
            print("Filer: Invalid 'd_ date spec!")
            sys.exit(2)
            
        now = datetime.now()
        
        if self.r[l] == 'y':
            date_str = now.strftime("%y")
            self.insert_string(date_str)
        elif self.r[l] == 'Y':
            date_str = now.strftime("%Y")
            self.insert_string(date_str)
        elif self.r[l] == 'm':
            date_str = now.strftime("%m")
            self.insert_string(date_str)
        elif self.r[l] == 'd':
            date_str = now.strftime("%d")
            self.insert_string(date_str)
        elif self.r[l] == 'M':
            date_str = now.strftime("%M")
            self.insert_string(date_str)
        elif self.r[l] == 'H':
            date_str = now.strftime("%H")
            self.insert_string(date_str)
        elif self.r[l] == 's':
            date_str = now.strftime("%Y%m%d")
            self.insert_string(date_str)
        elif self.r[l] == 't':
            date_str = now.strftime("%H%M")
            self.insert_string(date_str)
        else:
            print("Filer: Invalid 'd_ date spec!")
            sys.exit(2)
        
        return l + 1
    
    def rb_seq(self, l):
        """Handle sequence numbering in rebuilding pattern"""
        l += 1
        if l >= len(self.r):
            print("Filer: Invalid 's_ sequence spec!")
            sys.exit(2)
        
        try:
            digits = int(self.r[l])
            if digits < 1 or digits > 9:
                print("Filer: Sequence digit count must be 1-9!")
                sys.exit(2)
        except ValueError:
            print("Filer: Invalid 's_ sequence spec!")
            sys.exit(2)
        
        # Format the sequence number with the specified number of digits
        seq_str = str(self.seq_number).zfill(digits)
        self.insert_string(seq_str)
        
        return l + 1
    
    def insert_string(self, s):
        """Insert a string into the output name"""
        for char in s:
            if self.nnp < FNLEN:
                self.nn[self.nnp] = char
                self.nnp += 1
    
    def rb_copy(self, where):
        """Copy the table entry into the end of the rebuilt name"""
        tk = 1  # where in the table entry we are
        while tk < FNLEN and self.table[where][tk]:
            self.nn[self.nnp] = self.table[where][tk]
            self.nnp += 1
            tk += 1
    
    def get_digit(self, l):
        """Get digit from quote sequence"""
        if l + 1 >= len(self.r) or self.r[l + 1] != "'":
            return 0
        
        if l + 2 >= len(self.r):
            return 99
            
        try:
            d = int(self.r[l + 2])
            if 1 <= d <= 9:
                return d
            else:
                return 99
        except ValueError:
            return 99
    
    def get_rebuilt_name(self):
        """Get the rebuilt name as a string"""
        result = ""
        for i in range(self.nnp):
            if self.nn[i]:
                result += self.nn[i]
        return result
    
    def process_files(self, dirspec):
        """Process files in the specified directory"""
        try:
            files = os.listdir(dirspec)
        except OSError as e:
            print(f"Error reading directory {dirspec}: {e}")
            return
        
        for filename in files:
            # Clear out the table
            for k in range(10):
                self.clear_table_line(k)
            
            if self.match(filename, self.p, 0, 0, 0):
                self.rebuild()
                rebuilt_name = self.get_rebuilt_name()
                
                if self.quotenames:
                    print(f'{self.cmd} "{os.path.join(dirspec, filename)}" "{rebuilt_name}"')
                else:
                    print(f'{self.cmd} {os.path.join(dirspec, filename)} {rebuilt_name}')
                
                # Increment sequence number for next match
                self.seq_number += 1

def main():
    parser = argparse.ArgumentParser(
        description="Filer -- Pattern Matching File Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  filer.py -c cp -m "*b*" -r "*'2b*'1"
  Will turn: 'abc' into 'cba', etc.

In the match, * matches an arbitrary string, ? matches an arbitrary char.
In rebuilding: * or ? may be followed by 'n (n=1-9) to indicate which
               wild card char to replace.
                'd[yYmdHMst] inserts the indicated time:
                  'dY - insert the full year (1995)
                    y - short year (95)
                    m - month (01 thru 12)
                    d - day after first of the month (01 thru 31)
                    s - standard (yyyymmdd as: 19950922)
                    H - hours (00 thru 23)
                    M - minutes (00 thru 59)
                    t - time (hhmm)
                'sn - insert n-digit sequence number (starting at 1):
                  's3 - insert 001, 002, 003, etc.
                  's1 - insert 1, 2, 3, etc.
                  's5 - insert 00001, 00002, 00003, etc.

Actually, Filer just creates the commands to do that, you'll have to pipe
the commands to shell in order to get them to really happen.
        """)
    
    parser.add_argument('-m', '--match', dest='match_pattern', 
                       help='matching pattern')
    parser.add_argument('-r', '--rebuild', dest='rebuild_pattern', 
                       help='rebuilding pattern')
    parser.add_argument('-c', '--command', dest='command', default='',
                       help='a command to prefix to resulting matches and rebuilds')
    parser.add_argument('-d', '--directory', dest='directory', default='.',
                       help='directory in which to do matches')
    parser.add_argument('-a', '--all', action='store_true',
                       help='include files that begin with a period (.)')
    parser.add_argument('-q', '--quote', action='store_true',
                       help='quote filenames (useful for funny characters)')
    
    args = parser.parse_args()
    
    filer = Filer()
    filer.include_dots = args.all
    filer.quotenames = args.quote
    filer.cmd = args.command
    filer.p = args.match_pattern or ""
    filer.r = args.rebuild_pattern or ""
    
    filer.process_files(args.directory)

if __name__ == "__main__":
    main()
