// package main
package main

import (
	"embed"
	"flag"
	"fmt"
	"net/http"
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
	host  string
	port  int
	debug bool

	httplistenaddr string
)

func init() {
	flag.StringVar(&host, "host", "0.0.0.0", "HTTP API binding IP address")
	flag.StringVar(&host, "H", "0.0.0.0", "HTTP API binding IP address")
	flag.IntVar(&port, "port", 8088, "HTTP API binding port")
	flag.IntVar(&port, "P", 8088, "HTTP API binding port")
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
      Debug               %v
    --------------------------------------------------
`
	fmt.Printf(appBanner, httplistenaddr, debug)

}

func main() {
	router := mux.NewRouter()

	// STATIC ADMIN WEB UI
	router.PathPrefix("/").Handler(
		http.FileServer(
			http.FS(staticfiles),
		))

	// HEALTH CHECK
	router.HandleFunc("/healthcheck",
		func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(200)
			w.Write([]byte("OK"))
		}).Methods("GET")

	err := http.ListenAndServe(httplistenaddr, router)
	if err != nil {
		zlog.Fatal().Err(err).Str("module", "libresbc").Str("listen", httplistenaddr).
			Msg("Failed to start web service")
	}
}
