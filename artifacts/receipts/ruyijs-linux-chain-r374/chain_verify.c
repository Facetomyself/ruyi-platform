/* PKIX chain verification against caller-supplied trust anchors.
 *
 * The pinned adapter deliberately does not build a chain to a root; this
 * helper provides that missing step using NSS's own PKIX engine, so the trust
 * decision stays in NSS rather than in hand-written ASN.1 logic.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "cert.h"
#include "certdb.h"
#include "certt.h"
#include "nss.h"
#include "prerror.h"
#include "secerr.h"
#include "prinit.h"

/* NSS must be initialised before any certificate API. NSS_NoDB_Init avoids a
 * certificate database on disk; anchors arrive through the call itself. */
static char g_last_error[512];

__attribute__((visibility("default"))) const char *chain_last_error(void)
{
    return g_last_error;
}

/* Initialise NSS on a throwaway database directory. PKIX verification needs a
 * real cert DB handle: NSS_NoDB_Init leaves it unimplemented ("function not
 * implemented"), which would make every chain check fail for the wrong reason.
 * Anchors still arrive per call through cert_pi_trustAnchors. */
__attribute__((visibility("default"))) int chain_init(const char *dbdir)
{
    if (NSS_IsInitialized()) return 0;
    if (!dbdir || !dbdir[0]) return 900;
    if (NSS_InitReadWrite(dbdir) != SECSuccess) return (int)PR_GetError();
    return 0;
}

__attribute__((visibility("default"))) void chain_shutdown(void)
{
    if (NSS_IsInitialized()) NSS_Shutdown();
}

/* Parse a concatenation of length-prefixed DER certificates (adapter wire). */
static CERTCertList *chain_from_wire(const unsigned char *packed, size_t total)
{
    CERTCertList *list = CERT_NewCertList();
    size_t offset = 0;
    int count = 0;
    if (!list) return NULL;
    while (offset + 4 <= total) {
        uint32_t length = ((uint32_t)packed[offset] << 24) |
                          ((uint32_t)packed[offset + 1] << 16) |
                          ((uint32_t)packed[offset + 2] << 8) |
                          (uint32_t)packed[offset + 3];
        offset += 4;
        if (length == 0 || offset + length > total) {
            CERT_DestroyCertList(list);
            return NULL;
        }
        SECItem der = {siBuffer, (unsigned char *)(packed + offset), length};
        CERTCertificate *cert = CERT_NewTempCertificate(CERT_GetDefaultCertDB(), &der,
                                                        NULL, PR_FALSE, PR_TRUE);
        if (!cert) {
            CERT_DestroyCertList(list);
            return NULL;
        }
        offset += length;
        count++;
        if (CERT_AddCertToListTail(list, cert) != SECSuccess) {
            CERT_DestroyCertificate(cert);
            CERT_DestroyCertList(list);
            return NULL;
        }
    }
    if (offset != total || count == 0) {
        CERT_DestroyCertList(list);
        return NULL;
    }
    return list;
}

/* CERT_ReferenceCert is a static inline in newer NSS headers; reference the
 * leaf by its own pointer and let the chain list keep the original alive. */
static void cert_ref_retain(CERTCertificate **slot)
{
    (void)slot; /* the list still owns the certificate until it is destroyed */
}

/* Return 0 when the leaf chains to one of the anchors for the given host. */
__attribute__((visibility("default"))) int chain_verify(const unsigned char *packed, size_t packed_len,
                 const unsigned char *anchors, size_t anchors_len,
                 const char *host, const char *usage)
{
    CERTCertList *chain = NULL;
    CERTCertList *anchors_list = NULL;
    CERTCertificate *leaf = NULL;
    CERTCertListNode *node;
    CERTValInParam params[4];
    unsigned int index = 0;
    SECCertificateUsage usage_kind = certUsageSSLServer;
    int rc = 1;

    if (!packed || packed_len < 4 || !anchors || anchors_len < 4 || !host) return 2;
    if (usage && strcmp(usage, "client") == 0) usage_kind = certUsageSSLClient;

    chain = chain_from_wire(packed, packed_len);
    if (!chain) return 3;
    anchors_list = chain_from_wire(anchors, anchors_len);
    if (!anchors_list) { CERT_DestroyCertList(chain); return 4; }

    node = CERT_LIST_HEAD(chain);
    if (CERT_LIST_END(node, chain)) { CERT_DestroyCertList(anchors_list); CERT_DestroyCertList(chain); return 5; }
    leaf = node->cert;
    cert_ref_retain(&leaf);

    params[index].type = cert_pi_trustAnchors;
    params[index].value.pointer.chain = anchors_list;
    index++;
    /* Anchors are the only accepted trust source; AIA fetching would pull
     * certificates from the network, which this private transport forbids. */
    params[index].type = cert_pi_useOnlyTrustAnchors;
    params[index].value.scalar.b = PR_TRUE;
    index++;
    params[index].type = cert_pi_useAIACertFetch;
    params[index].value.scalar.b = PR_FALSE;
    index++;
    params[index].type = cert_pi_end;

    if (CERT_PKIXVerifyCert(leaf, usage_kind, params, NULL, NULL) == SECSuccess) {
        rc = (CERT_VerifyCertName(leaf, host) == SECSuccess) ? 0 : 6;
    } else {
        /* Surface the NSS error code so a failure is diagnosable instead of
         * a bare non-zero return. */
        rc = 100 + (int)PR_GetError();
        /* PR_ErrorToString is the only reliable decoder across error tables. */
        {
            const char *text = PR_ErrorToString(PR_GetError(), PR_LANGUAGE_I_DEFAULT);
            if (text) {
                size_t n = strlen(text);
                if (n > sizeof(g_last_error) - 1) n = sizeof(g_last_error) - 1;
                memcpy(g_last_error, text, n);
                g_last_error[n] = 0;
            }
        }
    }
    CERT_DestroyCertificate(leaf);
    CERT_DestroyCertList(anchors_list);
    CERT_DestroyCertList(chain);
    return rc;
}
