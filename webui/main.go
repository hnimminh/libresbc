// package main
package main

import (
	"crypto/tls"
	"embed"
	"flag"
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"github.com/rs/zerolog"
	zlog "github.com/rs/zerolog/log"
)

//go:embed assets index.html
var staticfiles embed.FS

var (
	host     string
	port     int
	debug    bool
	libresbc string

	httplistenaddr string
)

func init() {
	flag.StringVar(&host, "host", "0.0.0.0", "HTTP API binding IP address")
	flag.StringVar(&host, "H", "0.0.0.0", "HTTP API binding IP address")
	flag.IntVar(&port, "port", 8088, "HTTP API binding port")
	flag.IntVar(&port, "P", 8088, "HTTP API binding port")
	flag.StringVar(&libresbc, "libresbc", "http://127.0.0.1:8088", "LibreSBC web API interface")
	flag.StringVar(&libresbc, "L", "http://127.0.0.1:8088", "LibreSBC web API interface")
	flag.BoolVar(&debug, "debug", false, "sets log level to debug")
	flag.BoolVar(&debug, "d", false, "sets log level to debug")
	flag.Parse()

	// log setting
	output := zerolog.ConsoleWriter{}
	output.FormatLevel = func(i interface{}) string {
		return strings.ToUpper(fmt.Sprintf("[%4s]", i))
	}
	zlog.Logger = zlog.Output(
		zerolog.ConsoleWriter{
			Out:         os.Stderr,
			TimeFormat:  time.RFC3339,
			FormatLevel: output.FormatLevel,
			NoColor:     false},
	)
	zerolog.SetGlobalLevel(zerolog.InfoLevel)
	if debug {
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	}

	httplistenaddr = fmt.Sprintf("%s:%d", host, port)
	// startup banner with setting displayed
	appBanner := `
      +-+-+-+-+-+-+-+-+ +-+-+-+-+-+
      |L|I|B|R|E|S|B|C| |W|E|B|U|I|
      +-+-+-+-+-+-+-+ + +-+-+-+-+-+

      Open Source Session Border Controler
      LibreSBC - v0.0.0

      Listen              %s
      LibreSBC            %s
      Debug               %v
    --------------------------------------------------
`
	fmt.Printf(appBanner, httplistenaddr, libresbc, debug)

}

func main() {
	router := mux.NewRouter()

	// HEALTHCHECK FOR WEBUI
	router.HandleFunc("/healthcheck",
		func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(200)
			w.Write([]byte("OK"))
		}).Methods("GET")

	// PROXY TO LIBRESBC
	apiurl, err := url.Parse(libresbc)
	if err != nil {
		zlog.Fatal().Err(err).Str("module", "libresbc").Str("function", "webui").Str("action", "urlparse").
			Msg("Unable to parse libresbc web API URL")
	}
	proxy := httputil.NewSingleHostReverseProxy(apiurl)
	proxy.Transport = &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	router.PathPrefix("/libreapi").Handler(proxy)

	// STATIC ADMIN WEB UI
	router.PathPrefix("/").Handler(
		http.FileServer(
			http.FS(staticfiles),
		))

	// SERVE
	//--------------------------------------------------------------------------------
	if err := http.ListenAndServe(httplistenaddr, router); err != nil {
		zlog.Fatal().Err(err).Str("module", "libresbc").Str("listen", httplistenaddr).
			Msg("Failed to start web service")
	}
}
