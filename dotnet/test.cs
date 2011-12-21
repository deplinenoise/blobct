using BlobCt;
using System;
using System.IO;

namespace Fiskrens
{

    class Test
    {
        public static void Main(string[] args)
        {
            var m = new Moo();

            var a = new BlobArray<uint>();
            a.Add(89);
            a.Add(99);
            a.Add(109);
            m.Po = a;

            m.Text = "A string!";

			m.Array[0].Meh = 7;
			m.Array[1].Beh = 2.7f;
 
			m.Array2[0][1] = 2;

			BlobSerializer s = new BlobSerializer();
            s.BigEndian = false;
			s.Write(m);

            using (Stream data = File.OpenWrite("output"))
            using (Stream relocs = File.OpenWrite("output.relocs"))
            {
                s.GenerateOutput(data, relocs);
            }
		}
	}
}
