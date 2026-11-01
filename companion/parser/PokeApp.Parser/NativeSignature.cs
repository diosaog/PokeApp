using PKHeX.Core;
using System.Numerics;
using System.Security.Cryptography;

namespace PokeApp.Parser;

// Gen7's existing MemeCrypto verification, with fixed-width unsigned big-endian
// RSA output. PKHeX 24.11.11's MemeKey.Exponentiate writes short values at the
// start of a 96-byte buffer; leading-zero messages then fail its verifier.
// Algorithm adapted from the pinned PKHeX.Core MemeCrypto/MemeKey source under
// its existing GPL-3.0 notice (third-party/PKHeX-LICENSE.md). PUBLIC key only:
// signing stays in PKHeX. AES, SHA1 and checksum-table SHA256 checks are retained.
public static class NativeSignature
{
    private const string PublicKeyHex = "307C300D06092A864886F70D0101010500036B003068026100B61E192091F90A8F76A6EAAA9A3CE58C863F39AE253F037816F5975854E07A9A456601E7C94C29759FE155C064EDDFA111443F81EF1A428CF6CD32F9DAC9D48E94CFB3F690120E8E6B9111ADDAF11E7C96208C37C0143FF2BF3D7E831141A9730203010001";
    private static readonly byte[] Der = Convert.FromHexString(PublicKeyHex);
    private static readonly BigInteger Modulus = new(Der.AsSpan(0x18, 0x61), true, true);
    private static readonly BigInteger Exponent = new(Der.AsSpan(0x7B, 3), true, true);
    private const int RsaBytes = 96;

    public static bool VerifySave(ReadOnlySpan<byte> bytes)
    {
        if (bytes.Length is not (SaveUtil.SIZE_G7SM or SaveUtil.SIZE_G7USUM)) return false;
        bool ultra = bytes.Length == SaveUtil.SIZE_G7USUM;
        int start = (ultra ? 0x6C000 : 0x6BA00) + MemeCrypto.SaveFileSignatureOffset;
        var hash = SHA256.HashData(bytes.Slice(bytes.Length - 0x200, ultra ? 0x150 : 0x140));
        return Verify(bytes.Slice(start, MemeCrypto.SaveFileSignatureLength), hash);
    }

    internal static bool Verify(ReadOnlySpan<byte> signature, ReadOnlySpan<byte> checksumHash)
    {
        if (signature.Length != MemeCrypto.SaveFileSignatureLength || checksumHash.Length != SHA256.HashSizeInBytes)
            return false;
        var encoded = signature[^RsaBytes..];
        var value = new BigInteger(encoded, true, true);
        if (value >= Modulus) return false;
        var decoded = BigInteger.ModPow(value, Exponent, Modulus).ToByteArray(true, true);
        if (decoded.Length > RsaBytes) return false;
        var padded = new byte[RsaBytes];
        decoded.CopyTo(padded.AsSpan(RsaBytes - decoded.Length));
        if (DecryptMatches(signature, padded, checksumHash)) return true;
        padded[0] |= 0x80; // The original signer deliberately removes this bit.
        return DecryptMatches(signature, padded, checksumHash);
    }

    private static bool DecryptMatches(ReadOnlySpan<byte> signature, ReadOnlySpan<byte> rsa, ReadOnlySpan<byte> checksumHash)
    {
        var data = signature.ToArray();
        rsa.CopyTo(data.AsSpan(data.Length - RsaBytes));
        var payload = data.AsSpan(0, data.Length - RsaBytes);
        var sig = data.AsSpan(data.Length - RsaBytes);
        using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA1);
        sha.AppendData(Der); sha.AppendData(payload);
        var key = sha.GetHashAndReset().AsSpan(0, 16).ToArray();
        using var aes = Aes.Create(); aes.Key = key;
        var temp = new byte[16];
        var next = new byte[16];
        for (int i = sig.Length - 16; i >= 0; i -= 16)
        {
            Xor(temp, sig.Slice(i, 16));
            aes.DecryptEcb(temp, PaddingMode.None).CopyTo(temp, 0);
            temp.CopyTo(sig.Slice(i, 16));
        }
        Xor(temp, sig[^16..]);
        for (int i = 0; i < 16; i += 2)
        {
            next[i] = (byte)((2 * temp[i]) + (temp[i + 1] >> 7));
            next[i + 1] = (byte)(2 * temp[i + 1]);
            if (i + 2 < 16) next[i + 1] += (byte)(temp[i + 2] >> 7);
        }
        if ((temp[0] & 0x80) != 0) next[15] ^= 0x87;
        for (int i = 0; i < sig.Length; i += 16) Xor(sig.Slice(i, 16), next);
        Array.Clear(next);
        for (int i = 0; i < sig.Length; i += 16)
        {
            var part = sig.Slice(i, 16);
            part.CopyTo(temp);
            aes.DecryptEcb(part, PaddingMode.None).CopyTo(part);
            Xor(part, next);
            temp.CopyTo(next, 0);
        }
        var digest = SHA1.HashData(data.AsSpan(0, data.Length - 8));
        return CryptographicOperations.FixedTimeEquals(digest.AsSpan(0, 8), data.AsSpan(data.Length - 8))
            && CryptographicOperations.FixedTimeEquals(data.AsSpan(0, 32), checksumHash);
    }

    private static void Xor(Span<byte> destination, ReadOnlySpan<byte> other)
    {
        for (int i = 0; i < destination.Length; i++) destination[i] ^= other[i];
    }
}
