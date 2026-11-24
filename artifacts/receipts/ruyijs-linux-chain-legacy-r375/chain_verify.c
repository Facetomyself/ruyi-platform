/* Certificate chain verification with caller-supplied trust anchors.
 *
 * The pinned adapter does not build a path to a root. PKIX (CERT_PKIXVerifyCert)
 * is not implemented in this NSS build, so this helper uses the legacy chain
 * verifier instead: anchors are imported into a private temporary database and
 * marked trusted, then CERT_VerifyCertChain checks the leaf against them.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "cert.h"
#include "certdb.h"
#include "certt.h"
#include "nss.h"
#include "prerror.h"
#include "prinit.h"
#include "secerr.h"

static char g_last_error[512];

__attribute__((visibility("default"))) const char *chain_last_error(void)
{
    return g_last_error;
}

static void record_error(void)
{
    const char *text = PR_ErrorToString(PR_GetError(), PR_LANGUAGE_I_DEFAULT);
    size_t n;
    if (!text) { g_last_error[0] = 0; return; }
    n = strlen(text);
    if (n > sizeof(g_last_error) - 1) n = sizeof(g_last_error) - 1;
    memcpy(g_last_error, text, n);
    g_last_error[n] = 0;
}

__attribute__((visibility("default"))) int chain_init(const char *dbdir)
{
    if (NSS_IsInitialized()) return 0;
    if (!dbdir || !dbdir[0]) return 900;
    if (NSS_InitReadWrite(dbdir) != SECSuccess) { record_error(); return 901; }
    return 0;
}

__attribute__((visibility("default"))) void chain_shutdown(void)
{
    if (NSS_IsInitialized()) NSS_Shutdown();
}

/* Split a length-prefixed DER bundle into SECItems. Caller frees the array. */
static SECItem **split_wire(const unsigned char *packed, size_t total, unsigned int *count)
{
    SECItem **items = NULL;
    size_t offset = 0;
    unsigned int n = 0;
    if (!packed || total < 4) return NULL;
    /* Worst case one four-byte prefix per certificate. */
    items = (SECItem **)calloc(total / 4 + 1, sizeof(SECItem *));
    if (!items) return NULL;
    while (offset + 4 <= total) {
        uint32_t length = ((uint32_t)packed[offset] << 24) |
                          ((uint32_t)packed[offset + 1] << 16) |
                          ((uint32_t)packed[offset + 2] << 8) |
                          (uint32_t)packed[offset + 3];
        SECItem *item;
        offset += 4;
        if (length == 0 || offset + length > total) break;
        item = (SECItem *)calloc(1, sizeof(SECItem));
        if (!item) break;
        item->type = siBuffer;
        item->data = (unsigned char *)malloc(length);
        if (!item->data) { free(item); break; }
        memcpy(item->data, packed + offset, length);
        item->len = length;
        items[n++] = item;
        offset += length;
    }
    if (offset != total || n == 0) {
        unsigned int i;
        for (i = 0; i < n; i++) { free(items[i]->data); free(items[i]); }
        free(items);
        return NULL;
    }
    *count = n;
    return items;
}

static void free_items(SECItem **items, unsigned int count)
{
    unsigned int i;
    if (!items) return;
    for (i = 0; i < count; i++) {
        if (items[i]) { free(items[i]->data); free(items[i]); }
    }
    free(items);
}

/* Import every anchor into the temporary database and trust it for SSL. */
static int trust_anchors(const unsigned char *wire, size_t len)
{
    unsigned int count = 0;
    SECItem **items = split_wire(wire, len, &count);
    CERTCertificate **certs = NULL;
    CERTCertTrust trust;
    CERTCertDBHandle *db = CERT_GetDefaultCertDB();
    unsigned int i;
    SECStatus rc;
    if (!items) return 910;
    (void)0;
    memset(&trust, 0, sizeof(trust));
    trust.sslFlags = CERTDB_TRUSTED_CA | CERTDB_TRUSTED_CLIENT_CA | CERTDB_VALID_CA;
    trust.emailFlags = CERTDB_TRUSTED_CA | CERTDB_VALID_CA;
    trust.objectSigningFlags = CERTDB_TRUSTED_CA | CERTDB_VALID_CA;
    /* Only CA certificates may act as anchors. Importing an end-entity
     * certificate and trusting it would let the leaf vouch for itself. */
    for (i = 0; i < count; i++) {
        unsigned int type = 0;
        if (!CERT_IsCADERCert(items[i], &type)) {
            free_items(items, count);
            return 912; /* caller supplied a non-CA anchor */
        }
    }
    rc = CERT_ImportCerts(db, certUsageSSLCA, count, items, &certs, PR_FALSE, PR_FALSE, NULL);
    if (rc != SECSuccess) { record_error(); free_items(items, count); return 911; }
    for (i = 0; i < count; i++) {
        if (!certs[i]) continue;
        /* CERT_ChangeCertTrust writes through to the database entry, which is
         * what later lookups read; there is no exported in-memory setter. */
        if (CERT_ChangeCertTrust(db, certs[i], &trust) != SECSuccess) record_error();
    }
    if (certs) PORT_Free(certs);
    free_items(items, count);
    return 0;
}

/* Return 0 when the leaf chains to a trusted anchor and matches the host. */
__attribute__((visibility("default"))) int chain_verify(const unsigned char *packed, size_t packed_len,
                                                       const unsigned char *anchors, size_t anchors_len,
                                                       const char *host, const char *usage)
{
    unsigned int count = 0;
    SECItem **items = NULL;
    CERTCertificate *leaf = NULL;
    CERTCertDBHandle *db;
    SECCertUsage kind = certUsageSSLServer;
    int rc;

    if (!packed || packed_len < 4 || !anchors || anchors_len < 4 || !host) return 2;
    if (usage && strcmp(usage, "client") == 0) kind = certUsageSSLClient;

    rc = trust_anchors(anchors, anchors_len);
    if (rc) return rc;

    items = split_wire(packed, packed_len, &count);
    if (!items) return 920;
    db = CERT_GetDefaultCertDB();
    leaf = CERT_NewTempCertificate(db, items[0], NULL, PR_FALSE, PR_TRUE);
    if (!leaf) { record_error(); free_items(items, count); return 921; }
    free_items(items, count);

    /* CERT_VerifyCertChain is not exported by this build; CERT_VerifyCertNow
     * performs the same path and signature check against the database. */
    if (CERT_VerifyCertNow(db, leaf, PR_TRUE, kind, NULL) != SECSuccess) {
        record_error();
        CERT_DestroyCertificate(leaf);
        return 100 + (int)PR_GetError();
    }
    if (CERT_VerifyCertName(leaf, host) != SECSuccess) {
        record_error();
        CERT_DestroyCertificate(leaf);
        return 6;
    }
    CERT_DestroyCertificate(leaf);
    return 0;
}
