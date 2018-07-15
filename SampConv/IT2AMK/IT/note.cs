using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Diagnostics;

using IT2AMK.Util;
using static IT2AMK.Util.Util;

namespace IT2AMK.IT
{
	struct Note
	{
		public const int FADE = 253;
		public const int CUT = 254;
		public const int OFF = 255;
		public const int NONE = -1;

		private int _value;

		public int note
		{
			get {
				if (_value >= 0 && _value < 120) {
					return _value % 12;
				} else {
					throw new InvalidOperationException("Cannot get() the note of empty note or note cut/off/fade.");
				}
			}
			set {
				if (_value >= 0 && _value < 120) {
					if (value >= 0 && value < 12)
						_value = 12*(_value/12) + value;
					else
						throw new InvalidOperationException("Attempting to set() the note to an invalid value.");
				} else {
					throw new InvalidOperationException("Cannot set() the note of empty note or note cut/off/fade.");
				}
			}
		}

		public int octave
		{
			get {
				if (_value >= 0 && _value < 120) {
					return _value / 12;
				} else {
					throw new InvalidOperationException("Cannot get() the octave of empty note or note cut/off/fade.");
				}
			}
			set {
				if (_value >= 0 && _value < 120) {
					if (value >= 0 && value < 10)
						_value = 12*value + _value%12;
					else
						throw new InvalidOperationException("Attempting to set() the octave to an invalid value.");
				} else {
					throw new InvalidOperationException("Cannot set() the octave of empty note or note cut/off/fade.");
				}
			}
		}

		public string note_name
		{
			get {
				if (_value >= 0 && _value < 120) {
					string[] note_names = { "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" };
					return note_names[note];
				} else {
					if (_value == 255)
						return "===";
					else if (_value == 254)
						return "^^^";
					else if (_value < 0)
						return "---";
					else if (_value <= 253)
						return "~~~";
					else
						return "???";
				}
			}
		}

		public Note(int value)
		{
			if (value < 0)
				_value = -1;
			else if (value < 120)
				_value = value;
			else if (value < 253)
				_value = 253;
			else if (value < 256)
				_value = value;
			else
				throw new InvalidOperationException("Trying to initialize note with an invalid value.");
		}

		public Note(string name)
		{
			int[] letter_values = {9, 11, 0, 2, 4, 5, 7};
			if (name == "---") {
				_value = NONE;
			} else if (name == "~~~") {
				_value = FADE;
			} else if (name == "===") {
				_value = OFF;
			} else if (name == "^^^") {
				_value = CUT;
			} else if (!new Regex(@"^([a-g]|[A-G])(\#|b)?[0-9]$").Match(name).Success) {
				throw new InvalidOperationException("Trying to initialize note with an invalid name.");
			} else {
				_value = letter_values[char.ToUpper(name[0]) - 'A'];
				int num_index = 1;
				if (name[1] == '#') {
					_value++;
					num_index++;
				} else if (name[1] == 'b') {
					_value--;
					num_index++;
				}
				int x;
				Debug.Assert(Int32.TryParse(name[num_index].ToString(), out x));
				_value += 12*x;

				if (_value < 0)
					throw new InvalidOperationException("Trying to initialize note with an invalid value.");
				else if (_value >= 120)
					throw new InvalidOperationException("Trying to initialize note with an invalid value.");
			}
		}

		public override string ToString()
		{
			if (_value >= 0 && _value < 120)
				return note_name.PadRight(2, ' ') + octave.ToString();
			else
				return note_name;
		}

		public static Note operator + (Note n1, Note n2)
		{
			if (n1._value < 0 || n1._value >= 120 || n2._value < 0 || n2._value >= 120)
				throw new InvalidOperationException("Cannot perform + on empty notes or note cuts/offs/fades.");
			else
				return new Note(min(n1._value + n2._value, 119));
		}

		public static Note operator - (Note n1, Note n2)
		{
			if (n1._value < 0 || n1._value >= 120 || n2._value < 0 || n2._value >= 120)
				throw new InvalidOperationException("Cannot perform - on empty notes or note cuts/offs/fades.");
			else
				return new Note(max(n1._value - n2._value, 0));
		}

		public static Note operator + (Note n1, int n2)
		{
			if (n1._value < 0 || n1._value >= 120)
				throw new InvalidOperationException("Cannot perform + on empty notes or note cuts/offs/fades.");
			else
				return new Note(min(n1._value + n2, 119));
		}
		
		public static Note operator - (Note n1, int n2)
		{
			if (n1._value < 0 || n1._value >= 120)
				throw new InvalidOperationException("Cannot perform - on empty notes or note cuts/offs/fades.");
			else
				return new Note(max(n1._value - n2, 0));
		}

		public static Note operator ++ (Note n)
		{
			if (n._value < 0 || n._value >= 120)
				throw new InvalidOperationException("Cannot perform ++ on empty notes or note cuts/offs/fades.");
			else
				return new Note(min(n._value + 1, 119));
		}
		
		public static Note operator -- (Note n)
		{
			if (n._value < 0 || n._value >= 120)
				throw new InvalidOperationException("Cannot perform -- on empty notes or note cuts/offs/fades.");
			else
				return new Note(max(n._value - 1, 0));
		}

		public static Note operator << (Note n1, int n2)
		{
			return new Note(clamp(n1._value + 12*n2, 0, 119));
		}

		public static Note operator >> (Note n1, int n2)
		{
			return new Note(clamp(n1._value - 12*n2, 0, 119));
		}

		// Implicit conversions
		
		public static implicit operator Note (int n)
		{
			return new Note(n);
		}
		
		public static implicit operator Note (string s)
		{
			return new Note(s);
		}

		// Comparison operators (with other Note)
		
		public static bool operator == (Note n1, Note n2)
		{
			return n1.ToString() == n2.ToString();
		}
		
		public static bool operator != (Note n1, Note n2)
		{
			return !(n1 == n2);
		}

		public static bool operator < (Note n1, Note n2)
		{
			if (n1 == n2)
				return false;
			else
				return n1._value < n2._value;
		}
		
		public static bool operator > (Note n1, Note n2)
		{
			if (n1 == n2)
				return false;
			else
				return n1._value > n2._value;
		}
		
		public static bool operator <= (Note n1, Note n2)
		{
			return n1 < n2 || n1 == n2;
		}
		
		public static bool operator >= (Note n1, Note n2)
		{
			return n1 > n2 || n1 == n2;
		}

		// Have to override these I guess

		public override bool Equals(object obj)
		{
			if (!(obj is Note))
				return false;
			else
				return this == (Note)obj;
		}

		public override int GetHashCode()
		{
			return _value.GetHashCode();
		}
	}
}
