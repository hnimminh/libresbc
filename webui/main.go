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
	domain   string
	secure   bool
	certs    string

	httpListenAddr string
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
	flag.StringVar(&domain, "domain", "", "FQDN - Fully qualified domain name")
	flag.StringVar(&domain, "D", "", "FQDN - Fully qualified domain name")
	flag.BoolVar(&secure, "tls", false, "enable https server instead of default: http")
	flag.BoolVar(&secure, "t", false, "enable https server instead of default: http")
	flag.StringVar(&certs, "certs", "", "Declare SSL/TLS certificate/key files, syntax <crt:key>")
	flag.StringVar(&certs, "c", "", "Declare SSL/TLS certificate/key files, syntax <crt:key>")
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

	httpListenAddr = fmt.Sprintf("%s:%d", host, port)
	viaBrowserAddr := fmt.Sprintf("http://%s:%d", host, port)
	if secure {
		if domain == "" {
			zlog.Fatal().Msg("Domain is required for SSL/TLS")
		}
		if len(strings.Split(certs, ":")) != 2 {
			zlog.Fatal().Msg("Invalid syntax declare for tls cert files, eg. crt:key")
		}
		viaBrowserAddr = fmt.Sprintf("https://%s:%d", domain, port)
		if port == 443 {
			viaBrowserAddr = fmt.Sprintf("https://%s", domain)
		}
	}

	// startup banner with setting displayed
	appBanner := `
      +-+-+-+-+-+-+-+-+ +-+-+-+-+-+
      |L|I|B|R|E|S|B|C| |W|E|B|U|I|
      +-+-+-+-+-+-+-+-+ +-+-+-+-+-+

      Open Source Session Border Controler
      LibreSBC - v0.7.1.d

      Listen    %s
      LibreSBC  %s
      Debug     %v

      Access via browser at: %s
    --------------------------------------------------
`
	fmt.Printf(appBanner, httpListenAddr, libresbc, debug, viaBrowserAddr)

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
	router.PathPrefix("/apidocs").Handler(proxy)
	router.PathPrefix("/openapi.json").Handler(proxy)
	// STATIC ADMIN WEB UI
	router.PathPrefix("/").Handler(
		http.FileServer(
			http.FS(staticfiles),
		))

	// SERVER
	if secure {
		crtfile, keyfile := func(certs string) (string, string) {
			files := strings.Split(certs, ":")
			return files[0], files[1]
		}(certs)
		if err := http.ListenAndServeTLS(httpListenAddr, crtfile, keyfile, router); err != nil {
			zlog.Fatal().Err(err).Str("module", "libresbc").Str("listen", httpListenAddr).
				Msg("Failed to start web service with TLS")
		}
		return
	}

	if err := http.ListenAndServe(httpListenAddr, router); err != nil {
		zlog.Fatal().Err(err).Str("module", "libresbc").Str("listen", httpListenAddr).
			Msg("Failed to start web service")
	}
}
