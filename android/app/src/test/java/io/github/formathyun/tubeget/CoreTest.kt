package io.github.formathyun.tubeget

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CoreTest {

    @Test
    fun extractsUrlFromSharedText() {
        assertEquals(
            "https://youtu.be/abc123?si=x",
            extractUrl("Watch this! https://youtu.be/abc123?si=x"),
        )
        assertEquals("https://www.youtube.com/watch?v=a", extractUrl("(https://www.youtube.com/watch?v=a)."))
        assertNull(extractUrl("no link here"))
    }

    @Test
    fun videoArgsPreferResolutionThenH264() {
        val a = Args.download(DownloadOptions(maxHeight = 1080, container = "mp4"), "/out", "/tmp")
        val s = a[a.indexOf("-S") + 1]
        assertEquals("res:1080,vcodec:h264,acodec:aac,ext:mp4:m4a", s)
        assertEquals("bv*+ba/b", a[a.indexOf("-f") + 1])
        assertTrue("--embed-thumbnail" in a && "--embed-metadata" in a)
        assertEquals("temp:/tmp", a[a.lastIndexOf("-P") + 1])
    }

    @Test
    fun audioArgs() {
        val a = Args.download(DownloadOptions(mode = "audio", audioFormat = "m4a"), "/out", "/tmp")
        assertTrue("-x" in a)
        assertEquals("m4a", a[a.indexOf("--audio-format") + 1])
        assertEquals("0", a[a.indexOf("--audio-quality") + 1])
        assertTrue("--merge-output-format" !in a)
    }

    @Test
    fun playlistTemplate() {
        val t = Args.outputTemplate(DownloadOptions(playlistTitle = "My: List 100%", index = 3))
        assertEquals("My_ List 100%%/03 - %(title).150B [%(id)s].%(ext)s", t)
    }

    @Test
    fun progressCombinesTwoStreams() {
        val p = ProgressTracker()
        p.feed("TGR|1000|500|NA")
        p.feed("TGP|downloading|500|1000|NA|100|5|NA|NA|/tmp/a.f137.mp4.part")
        assertEquals(500f / 1500f, p.fraction!!, 0.001f)
        p.feed("TGP|finished|1000|1000|NA|NA|NA|NA|NA|/tmp/a.f137.mp4.part")
        p.feed("TGP|downloading|250|500|NA|100|2|NA|NA|/tmp/a.f140.m4a.part")
        assertEquals(1250f / 1500f, p.fraction!!, 0.001f)
        p.feed("TGS|postprocess")
        assertTrue(p.postprocessing)
        p.feed("TGF|/storage/emulated/0/Download/TubeGet/a.mp4")
        assertEquals("/storage/emulated/0/Download/TubeGet/a.mp4", p.finalPath)
    }

    @Test
    fun progressWithoutSizesUsesParts() {
        val p = ProgressTracker()
        p.feed("TGR|NA|NA|NA")
        p.feed("TGP|downloading|NA|NA|NA|NA|NA|5|10|/tmp/x.part")
        assertEquals(0.5f, p.fraction!!, 0.001f)
    }

    @Test
    fun parsesVideoInfo() {
        val json = """
            {"id":"abc","title":"Song","uploader":"Artist","duration":200,"thumbnail":"https://i/t.jpg",
             "webpage_url":"https://www.youtube.com/watch?v=abc",
             "formats":[
               {"format_id":"sb0","protocol":"mhtml","vcodec":"none","acodec":"none"},
               {"format_id":"140","vcodec":"none","acodec":"mp4a.40.2","abr":128,"filesize":3000000},
               {"format_id":"137","vcodec":"avc1","acodec":"none","width":1920,"height":1080,"tbr":2500,"filesize":50000000},
               {"format_id":"136","vcodec":"avc1","acodec":"none","width":1280,"height":720,"tbr":1200,"filesize":20000000},
               {"format_id":"18","vcodec":"avc1","acodec":"mp4a","width":640,"height":360,"tbr":500}
             ]}
        """.trimIndent()
        val info = InfoParser.parse(json, "https://youtu.be/abc")
        assertEquals("Song", info.title)
        assertEquals(listOf(1080, 720, 360), info.heights)
        assertEquals(53_000_000L, info.videoSizes[1080])
        assertEquals(23_000_000L, info.videoSizes[720])
        assertEquals(53_000_000L, info.videoSizes[0])
        assertEquals(3_000_000L, info.audioSize)
    }

    @Test
    fun shortsUseSmallerSide() {
        val json = """{"id":"s","title":"Short","formats":[
            {"vcodec":"vp9","acodec":"none","width":1080,"height":1920,"tbr":3000}]}"""
        assertEquals(listOf(1080), InfoParser.parse(json, "u").heights)
    }

    @Test
    fun parsesPlaylist() {
        val json = """{"_type":"playlist","id":"PL1","title":"Mix","entries":[
            {"id":"a","title":"One","url":"https://www.youtube.com/watch?v=a","duration":61},
            {"id":"b","title":"Two"}]}"""
        val info = InfoParser.parse(json, "u")
        assertTrue(info.isPlaylist)
        assertEquals(2, info.entries.size)
        assertEquals("https://www.youtube.com/watch?v=b", info.entries[1].url)
        assertEquals(2, info.entries[1].index)
    }

    @Test
    fun dubAndSubtitleArgsMatchPc() {
        val v = Args.download(DownloadOptions(dubLang = "en", subLangs = "ko,en", subMode = "embed"), "/o", "/t")
        assertEquals("bv*+ba[language^=en]/bv*+ba/b", v[v.indexOf("-f") + 1])
        assertEquals("ko,en", v[v.indexOf("--sub-langs") + 1])
        assertTrue("--embed-subs" in v && "no-keep-subs" in v && "--convert-subs" !in v)

        val both = Args.download(DownloadOptions(subLangs = "ko", subMode = "both"), "/o", "/t")
        assertTrue("--embed-subs" in both && "--convert-subs" in both && "no-keep-subs" !in both)

        val audio = Args.download(DownloadOptions(mode = "audio", dubLang = "ja", subLangs = "ko"), "/o", "/t")
        assertEquals("ba[language^=ja]/ba/b", audio[audio.indexOf("-f") + 1])
        assertTrue("--embed-subs" !in audio && "--convert-subs" in audio)
    }

    @Test
    fun audioQualityArgs() {
        val a = Args.download(DownloadOptions(mode = "audio", audioFormat = "mp3", audioQuality = "192K"), "/o", "/t")
        assertEquals("192K", a[a.indexOf("--audio-quality") + 1])
        val flac = Args.download(DownloadOptions(mode = "audio", audioFormat = "flac", audioQuality = "192K"), "/o", "/t")
        assertTrue("--audio-quality" !in flac)
    }

    @Test
    fun tagArgs() {
        val custom = Args.download(
            DownloadOptions(mode = "audio", tagValues = mapOf("title" to "Way Less Sad", "artist" to "AJR", "album" to "")),
            "/o", "/t",
        )
        assertTrue("#Way Less Sad:#(?P<meta_title>.*)" in custom)
        assertTrue(":(?P<meta_album>)" in custom)

        val off = Args.download(DownloadOptions(mode = "audio", embedMetadata = false), "/o", "/t")
        assertTrue("--embed-metadata" !in off && "ExtractAudio:-map_metadata -1" in off)

        val smart = Args.download(DownloadOptions(tagSmart = true), "/o", "/t")
        assertTrue("--replace-in-metadata" in smart)
    }

    @Test
    fun guessesTagsFromTitle() {
        val info = InfoParser.parse("""{"id":"x","title":"AJR - Way Less Sad (Official Video)","uploader":"AJR","upload_date":"20210304"}""", "u")
        val t = Tags.guess(info)
        assertEquals("AJR", t["artist"])
        assertEquals("Way Less Sad", t["title"])
        assertEquals("2021", t["year"])
    }

    @Test
    fun parsesSubtitlesAndDubs() {
        val json = """{"id":"d","title":"T",
            "subtitles":{"ko":[{"ext":"vtt","name":"Korean"}],"live_chat":[{"ext":"json"}]},
            "automatic_captions":{"en-orig":[{"name":"English (Original)"}],"ja":[{"name":"Japanese"}]},
            "formats":[
              {"vcodec":"none","acodec":"opus","language":"en","format_note":"English original, high","abr":130},
              {"vcodec":"none","acodec":"opus","language":"ko","format_note":"Korean dubbed","abr":130}]}"""
        val info = InfoParser.parse(json, "u")
        assertEquals(mapOf("ko" to "Korean"), info.subtitles)
        assertEquals(setOf("en-orig", "ja"), info.autoCaptions.keys)
        assertEquals("original", info.dubs["en"])
        assertEquals("dubbed", info.dubs["ko"])
    }

    @Test
    fun optionsRoundTripJson() {
        val o = DownloadOptions(dubLang = "en", tagValues = mapOf("title" to "A"), outDir = "Documents/TubeGet", subMode = "both")
        assertEquals(o, DownloadOptions.fromJson(o.toJson()))
    }

    @Test
    fun sanitizesNames() {
        assertEquals("a_b_c", sanitizeName("a/b:c"))
        assertEquals("TubeGet", sanitizeName("..."))
    }
}
