// vim: syntax=cs ts=4 sw=4 noexpandtab foldmethod=marker

using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Collections.Generic;

namespace BlobCt
{
    public class BlobException : Exception
    {
        public BlobException(string message) : base(message)
        {}
    }

	public interface IPointerTarget<T>
	{
		T this [int index] { get; set; }
		void Align(BlobSerializer s);
		void WriteValue(BlobSerializer s);
		void ValidateOffset(int Offset);
	}

	interface IBlobTypeDescriptor<T>
	{
		void Align(BlobSerializer s, T val);
		void WriteValue(BlobSerializer s, T val);
		void WriteSequence(BlobSerializer s, IEnumerable<T> seq);
	}

	// {{{ IntTypeDescriptor
	class IntTypeDescriptor : IBlobTypeDescriptor<int>
	{
		private IntTypeDescriptor() {}
		public static readonly IntTypeDescriptor Instance = new IntTypeDescriptor();

		public void Align(BlobSerializer s, int val)
		{
			s.Align(s.IntAlignment);
		}

		public void WriteValue(BlobSerializer s, int val)
		{
			s.WriteInt(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<int> seq)
		{
			foreach (int val in seq)
				s.WriteInt(val);
		}
	}
	// }}}

	// {{{ UintTypeDescriptor
	class UintTypeDescriptor : IBlobTypeDescriptor<uint>
	{
		private UintTypeDescriptor() {}
		public static readonly UintTypeDescriptor Instance = new UintTypeDescriptor();

		public void Align(BlobSerializer s, uint val)
		{
			s.Align(s.IntAlignment);
		}

		public void WriteValue(BlobSerializer s, uint val)
		{
			s.WriteUint(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<uint> seq)
		{
			foreach (uint val in seq)
				s.WriteUint(val);
		}
	}
	/// }}}

	// {{{ FloatTypeDescriptor
	class FloatTypeDescriptor : IBlobTypeDescriptor<float>
	{
		private FloatTypeDescriptor() {}
		public static readonly FloatTypeDescriptor Instance = new FloatTypeDescriptor();

		public void Align(BlobSerializer s, float val)
		{
			s.Align(s.FloatAlignment);
		}

		public void WriteValue(BlobSerializer s, float val)
		{
			s.WriteFloat(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<float> seq)
		{
			foreach (float val in seq)
				s.WriteFloat(val);
		}
	}
	// }}}

	// {{{ StringTypeDescriptor
	class StringTypeDescriptor : IBlobTypeDescriptor<string>
	{
		private StringTypeDescriptor() {}
		public static readonly StringTypeDescriptor Instance = new StringTypeDescriptor();

		public void Align(BlobSerializer s, string val)
		{
			s.Align(s.PointerAlignment);
		}

		public void WriteValue(BlobSerializer s, string val)
		{
			s.WriteStringPointer(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<string> seq)
		{
			foreach (string val in seq)
				s.WriteStringPointer(val);
		}
	}
	// }}}

	// {{{ ShortTypeDescriptor 
	class ShortTypeDescriptor : IBlobTypeDescriptor<short>
	{
		private ShortTypeDescriptor() {}
		public static readonly ShortTypeDescriptor Instance = new ShortTypeDescriptor();

		public void Align(BlobSerializer s, short val)
		{
			s.Align(s.ShortAlignment);
		}

		public void WriteValue(BlobSerializer s, short val)
		{
			s.WriteShort(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<short> seq)
		{
			foreach (short val in seq)
				s.WriteShort(val);
		}
	}
	// }}}

	// {{{ UshortTypeDescriptor
	class UshortTypeDescriptor : IBlobTypeDescriptor<ushort>
	{
		private UshortTypeDescriptor() {}
		public static readonly UshortTypeDescriptor Instance = new UshortTypeDescriptor();

		public void Align(BlobSerializer s, ushort val)
		{
			s.Align(s.ShortAlignment);
		}

		public void WriteValue(BlobSerializer s, ushort val)
		{
			s.WriteUshort(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<ushort> seq)
		{
			foreach (ushort val in seq)
				s.WriteUshort(val);
		}
	}
	// }}}

	// {{{ ByteTypeDescriptor
	class ByteTypeDescriptor : IBlobTypeDescriptor<byte>
	{
		private ByteTypeDescriptor() {}
		public static readonly ByteTypeDescriptor Instance = new ByteTypeDescriptor();

		public void Align(BlobSerializer s, byte val)
		{ }

		public void WriteValue(BlobSerializer s, byte val)
		{
			s.WriteByte(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<byte> seq)
		{
			foreach (byte val in seq)
				s.WriteByte(val);
		}
	}
	// }}}

	// {{{ ArrayTypeDescriptor<T>
	class ArrayTypeDescriptor<T> : IBlobTypeDescriptor<BlobArray<T>>
	{
		private readonly IBlobTypeDescriptor<T> m_elemDesc;

		public ArrayTypeDescriptor(BlobSerializer s)
		{
			m_elemDesc = s.GetDescriptor<T>();
		}

		public void Align(BlobSerializer s, BlobArray<T> val)
		{
			if (val.Count > 0)
				m_elemDesc.Align(s, val[0]);
		}

		public void WriteValue(BlobSerializer s, BlobArray<T> val)
		{
			IBlobTypeDescriptor<T> desc = m_elemDesc;
			foreach (T v in val) {
				desc.WriteValue(s, v);
			}
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<BlobArray<T>> seq)
		{
			IBlobTypeDescriptor<T> desc = m_elemDesc;
			foreach (BlobArray<T> val in seq)
			{
				foreach (T v in val) {
					desc.WriteValue(s, v);
				}
			}
		}
	}
	// }}}

	// {{{ PointerTypeDescriptor<T>
	class PointerTypeDescriptor<T> : IBlobTypeDescriptor<Pointer<T>>
	{
		public PointerTypeDescriptor(BlobSerializer s)
		{
		}

		public void Align(BlobSerializer s, Pointer<T> val)
		{
			s.Align(s.PointerAlignment);
		}

		public void WriteValue(BlobSerializer s, Pointer<T> val)
		{
			s.WritePointer(val);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<Pointer<T>> seq)
		{
			foreach (Pointer<T> val in seq)
				s.WritePointer(val);
		}
	}
	// }}}

	// {{{ BlobSerializableDesc<T>
	class BlobSerializableDesc<T> : IBlobTypeDescriptor<T>
	{
		public BlobSerializableDesc(BlobSerializer s)
		{
		}

		public void Align(BlobSerializer s, T val)
		{
			((IPointerTarget<T>)val).Align(s);
		}

		public void WriteValue(BlobSerializer s, T val)
		{
			((IPointerTarget<T>)val).WriteValue(s);
		}

		public void WriteSequence(BlobSerializer s, IEnumerable<T> seq)
		{
			foreach (T val in seq)
				((IPointerTarget<T>)val).WriteValue(s);
		}
	}
	// }}}

	// {{{ BlobSerializer
	public class BlobSerializer
    {
        public byte PaddingByte { get; set; }
        public bool BigEndian { get; set; }

        public byte PointerSize { get; set; }

        public int ShortAlignment { get; set; }
        public int IntAlignment { get; set; }
        public int FloatAlignment { get; set; }
        public byte PointerAlignment { get; set; }

        private class Segment
        {
			public int Align = 0;
            public readonly MemoryStream Stream = new MemoryStream();
            public Segment Next, Prev;
        }
        
        private struct Locator
        {
            public Segment Segment;
            public long Offset;
        }

        private struct Relocation
        {
            public Locator Source;
            public Locator Target;
        }

        private Dictionary<object, Locator> m_locators = new Dictionary<object, Locator>();
        private List<Relocation> m_relocs = new List<Relocation>();

        public BlobSerializer()
        {
            m_firstSegment = new Segment();
            SetSegment(m_firstSegment);

            PaddingByte = 0x00;
            BigEndian = true;
            PointerSize = 4;
            PointerAlignment = 4;
            ShortAlignment = 2;
            FloatAlignment = 4;
            IntAlignment = 4;
        }

        private Segment m_firstSegment;
        private Segment m_stringSegment;
        private Segment m_segment;
        private Stream m_stream;

		private void AlignStream(Stream s, int size)
		{
            Debug.Assert((size & ~(size - 1)) == size);
            long pos = s.Position;
            long alignedPos = (pos + size - 1) & ~(size - 1);
            while (alignedPos > pos) {
                s.WriteByte(PaddingByte);
            }
		}

		public void Align(int size)
		{
			if (m_segment.Align == 0)
				m_segment.Align = size;

			AlignStream(m_stream, size);
		}

        private void SetSegment(Segment s)
        {
            m_segment = s;
            m_stream = s.Stream;
        }
		
		private void PushSegment()
		{
            Segment s = m_segment.Next;

            if (null == s) {
                s = new Segment { Prev = m_segment };
                m_segment.Next = s;
            }

            SetSegment(s);
		}
		
		private void PopSegment()
		{
            SetSegment(m_segment.Prev);
		}

        private Locator CurrentPos()
        {
            return new Locator { Segment = m_segment, Offset = m_stream.Position };
        }
		
		public void WriteByte(byte b)
        {
            m_stream.WriteByte(b);
        }

        private static byte SelB(uint val, int byteIndex)
        {
            return (byte) ((val >> (byteIndex * 8)) & 0xff);
        }

        private static byte SelB(int val, int byteIndex)
        {
            return (byte) ((val >> (byteIndex * 8)) & 0xff);
        }

		public void WriteUshort(ushort b)
        {
            Align(ShortAlignment);
            Stream s = m_stream;
            if (BigEndian)
            {
                s.WriteByte(SelB(b, 1));
                s.WriteByte(SelB(b, 0));
            }
            else
            {
                s.WriteByte(SelB(b, 0));
                s.WriteByte(SelB(b, 1));
            }
        }

		private void WriteUint(Stream s, uint b)
        {
            AlignStream(s, IntAlignment);
            if (BigEndian)
            {
                s.WriteByte(SelB(b, 3));
                s.WriteByte(SelB(b, 2));
                s.WriteByte(SelB(b, 1));
                s.WriteByte(SelB(b, 0));
            }
            else
            {
                s.WriteByte(SelB(b, 0));
                s.WriteByte(SelB(b, 1));
                s.WriteByte(SelB(b, 2));
                s.WriteByte(SelB(b, 3));
            }
        }

		public void WriteUint(uint b)
        {
			WriteUint(m_stream, b);
        }

		public void WriteSbyte(sbyte b) { WriteByte((byte)b); }
		public void WriteShort(short b) { WriteUshort((ushort)b); }
		public void WriteInt(int b) { WriteUint((uint)b); }

		public void WriteFloat(float b)
        {
            byte[] data = BitConverter.GetBytes(b);

            if (BitConverter.IsLittleEndian && this.BigEndian)
                Array.Reverse(data);

            Align(IntAlignment);
            m_stream.Write(data, 0, 4);
        }

		private void WritePointerValue(Stream s, long val)
		{
            // Write size of a pointer. For null pointers,
            // these will be untouched. For real pointers, we will go back and
            // fix them up later via the m_relocs list.
			if (BigEndian)
			{
				for (int i = (PointerSize-1) * 8; i >= 0; i -= 8)
					s.WriteByte((byte) ((val >> i) & 0xff));
			}
			else
			{
				for (int i = 0, end = (PointerSize) * 8; i < end; i += 8)
					s.WriteByte((byte) ((val >> i) & 0xff));
			}
		}

		public void WritePointer<T>(Pointer<T> t)
        {
            Align(PointerAlignment);
            Stream stream = m_stream;

            if (t.Target != null)
            {
                Locator position;
                if (!m_locators.TryGetValue(t.Target, out position))
                {
                    PushSegment();
                    position = m_locators[t] = CurrentPos();
                    Write(t.Target);
                    PopSegment();
                }
                m_relocs.Add(new Relocation { Source = CurrentPos(), Target = position });
            }

			WritePointerValue(stream, 0);
 		}

		private Dictionary<string, Locator> m_strings = new Dictionary<string, Locator>();

		private Locator GetStringLocator(string t)
        {
			// Could optimize this by writing strings when all data is
			// collected to map substrings onto longer strings.

			Locator loc;
			if (m_strings.TryGetValue(t, out loc))
				return loc;

			if (m_stringSegment == null)
				m_stringSegment = new Segment();

			loc = new Locator {
				Segment = m_stringSegment,
				Offset = (int) m_stringSegment.Stream.Position
			};

			byte[] data = Encoding.UTF8.GetBytes(t);
			m_stringSegment.Stream.Write(data, 0, data.Length);
			m_stringSegment.Stream.WriteByte(0);

			m_strings[t] = loc;

			return loc;
		}

		public void WriteStringPointer(string t)
        {
            if (t != null)
            {
                Locator position = GetStringLocator(t);
                m_relocs.Add(new Relocation { Source = CurrentPos(), Target = position });
            }

			WritePointerValue(m_stream, 0);
        }

		public void Write<T>(IPointerTarget<T> obj)
		{
			obj.Align(this);
			obj.WriteValue(this);
		}

		private Dictionary<Type, object> m_typeDesc = new Dictionary<Type, object>();
		
		private object CreateGenericDesc(Type gt, Type p0)
		{
			Type descType = gt.MakeGenericType(p0);
			return Activator.CreateInstance(descType, this);
		}

		private object CreateDescriptorImpl(Type t)
		{
			if (t == typeof(int))
				return IntTypeDescriptor.Instance;
			if (t == typeof(uint))
				return UintTypeDescriptor.Instance;
			if (t == typeof(short))
				return ShortTypeDescriptor.Instance;
			if (t == typeof(ushort))
				return UshortTypeDescriptor.Instance;
			if (t == typeof(byte))
				return ByteTypeDescriptor.Instance;
			if (t == typeof(float))
				return FloatTypeDescriptor.Instance;
			if (t == typeof(string))
				return StringTypeDescriptor.Instance;

			if (t.IsGenericType)
			{
				Type gendef = t.GetGenericTypeDefinition();

				if (gendef == typeof(BlobArray<>))
				{
					Type t1 = t.GetGenericArguments()[0];
					return CreateGenericDesc(typeof(ArrayTypeDescriptor<>), t1);
				}
				else if (gendef == typeof(Pointer<>))
				{
					Type t1 = t.GetGenericArguments()[0];
					return CreateGenericDesc(typeof(PointerTypeDescriptor<>), t1);
				}
			}

			foreach (Type i in t.GetInterfaces())
			{
				if (i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IPointerTarget<>))
				{
					Type t1 = i.GetGenericArguments()[0];
					if (t1 != t)
					{
						throw new BlobException(t + " should implement IPointerTarget<" +
								t + ">, but really implements " + i);
					}

					return CreateGenericDesc(typeof(BlobSerializableDesc<>), t);
				}
			}

			throw new BlobException("unsupported type " + t);
		}

		private object GetDescriptorImpl(Type t)
		{
			object o;

			if (!m_typeDesc.TryGetValue(t, out o)) {
				o = m_typeDesc[t] = CreateDescriptorImpl(t);
			}

			return o;
		}

		internal IBlobTypeDescriptor<T> GetDescriptor<T>()
		{
			return (IBlobTypeDescriptor<T>) GetDescriptorImpl(typeof(T));
		}

		private void WriteSeg(Segment s, Stream o, Dictionary<Segment, long> segPos)
		{
			if (s.Align > 1)
				AlignStream(o, s.Align);
			segPos[s] = o.Position;
			s.Stream.WriteTo(o);
		}

		public void GenerateOutput(Stream output, Stream relocations)
		{
			var segPos = new Dictionary<Segment, long>();

			Segment s = m_firstSegment;
			while (s != null)
			{
				WriteSeg(s, output, segPos);
				s = s.Next;
			}

			if (m_stringSegment != null)
				WriteSeg(m_stringSegment, output, segPos);

			foreach (var r in m_relocs)
			{
				var source = r.Source;
				var target = r.Target;

				long off = segPos[source.Segment] + source.Offset;
				long dst = segPos[target.Segment] + target.Offset;

				long delta = dst - off;

				output.Position = off;
				WritePointerValue(output, delta);

				WriteUint(relocations, (uint) off);
			}
		}
	}
	// }}}
	
	// {{{ BlobArray<T>
	public sealed class BlobArray<T> : IList<T>, IPointerTarget<T>
	{
		private readonly IList<T> m_storage;

		public BlobArray()
		{
            m_storage = new List<T>();
		}

        public BlobArray(int fixedSize)
		{
            m_storage = new T[fixedSize];
		}
		
		public int IndexOf(T item)
        {
            return m_storage.IndexOf(item);
        }

		public void Insert(int index, T item)
        {
            m_storage.Insert(index, item);
        }

		public void RemoveAt(int index)
        {
            m_storage.RemoveAt(index);
        }

		public T this [int index]
        {
			get { return m_storage[index]; }
			set { m_storage[index] = value; }
		}

		public System.Collections.IEnumerator GetEnumerator()
		{
			return m_storage.GetEnumerator();
		}

		IEnumerator<T> IEnumerable<T>.GetEnumerator()
		{
			return m_storage.GetEnumerator();
		}

		public void Add(T item) { m_storage.Add(item); }
		public void Clear() { m_storage.Clear(); }
		public bool Contains(T item) { return m_storage.Contains(item); }
		public void CopyTo(T[] array, int arrayIndex) { m_storage.CopyTo(array, arrayIndex); }
		public bool Remove(T item) { return m_storage.Remove(item); }
		public int Count { get { return m_storage.Count; } }
		public bool IsReadOnly { get { return false; } }

		public static implicit operator Pointer<T>(BlobArray<T> obj)
		{
			return new Pointer<T> { Target = obj };
		}

		public Pointer<T> GetElemPointer(int elem)
		{
			if (elem < 0 || elem >= Count)
				throw new BlobException("Pointer past array");
			return new Pointer<T> { Target = this, Offset = elem };
		}

		void IPointerTarget<T>.Align(BlobSerializer s)
		{
			if (Count > 0)
				s.GetDescriptor<T>().Align(s, this[0]);
		}

		void IPointerTarget<T>.WriteValue(BlobSerializer s)
		{
			s.GetDescriptor<T>().WriteSequence(s, this);
		}
		
		void IPointerTarget<T>.ValidateOffset(int offset)
		{
			if (offset < 0 || offset > this.Count)
				throw new ApplicationException();
		}
	}
	// }}}
	
	// {{{ Pointer<T>
	public struct Pointer<T>
	{
		public IPointerTarget<T> Target;
		public int Offset;

		public T this [int index]
		{
			get
			{
				if (null == Target)
					throw new BlobException("cannot deref null pointer");
				return Target[index];
			}
			set
			{
				if (null == Target)
					throw new BlobException("cannot deref null pointer");
				Target[index] = value;
			}
		}
	}
	// }}}
}
